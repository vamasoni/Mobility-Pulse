TRUNCATE staging.dot_traffic, staging.tlc_yellow, staging.collisions, clean.dim_weather, analytics.fact_traffic_15min, analytics.fact_traffic_hourly, analytics.fact_trips_hourly, analytics.fact_incidents, analytics.hourly_traffic_enriched;

INSERT INTO staging.dot_traffic
SELECT
 NULLIF(payload->>'id','')::bigint,
 NULLIF(payload->>'speed','')::double precision,
 NULLIF(payload->>'travel_time','')::double precision,
 NULLIF(payload->>'status','')::integer,
 NULLIF(payload->>'data_as_of','')::timestamptz,
 NULLIF(payload->>'link_id','')::bigint,
 payload->>'link_points', payload->>'encoded_poly_line', payload->>'encoded_poly_line_lvls',
 payload->>'owner', NULLIF(payload->>'transcom_id','')::bigint,
 payload->>'borough', payload->>'link_name', source_date, loaded_at
FROM raw.dot_traffic;

INSERT INTO staging.tlc_yellow
SELECT
 pickup_ts::timestamp, dropoff_ts::timestamp, passenger_count, trip_distance,
 pu_location_id, do_location_id, fare_amount, tip_amount, total_amount,
 congestion_surcharge, cbd_congestion_fee, source_month, row_hash
FROM raw.tlc_yellow
WHERE pickup_ts IS NOT NULL AND dropoff_ts IS NOT NULL;

INSERT INTO clean.dim_weather
SELECT DISTINCT ON (ts_local)
 ts_local::timestamp, temperature_2m, relative_humidity_2m, apparent_temperature,
 precipitation, rain, snowfall, weather_code, cloud_cover, wind_speed_10m, wind_gusts_10m, now()
FROM raw.weather
ORDER BY ts_local;

INSERT INTO staging.collisions
SELECT collision_id,
 (crash_date || ' ' || COALESCE(crash_time,'00:00'))::timestamp,
 borough, latitude, longitude, COALESCE(persons_injured,0), COALESCE(persons_killed,0),
 CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN ST_SetSRID(ST_MakePoint(longitude,latitude),4326) END
FROM raw.collisions
WHERE collision_id IS NOT NULL;

INSERT INTO analytics.fact_incidents
SELECT incident_id, ts_local, borough, latitude, longitude,
 CASE WHEN persons_killed>0 THEN 'fatal'
      WHEN persons_injured>0 THEN 'injury' ELSE 'property_damage' END,
 CASE WHEN persons_killed>0 THEN 3 WHEN persons_injured>0 THEN 2 ELSE 1 END,
 persons_injured, persons_killed, geom
FROM staging.collisions
ON CONFLICT (incident_id) DO UPDATE SET ts_local=EXCLUDED.ts_local;

INSERT INTO analytics.fact_traffic_15min
WITH x AS (
 SELECT id segment_id, date_bin('15 minutes',data_as_of,'2000-01-01') ts,
        speed,travel_time
 FROM staging.dot_traffic
 WHERE speed BETWEEN 0 AND 120 AND travel_time>0 AND data_as_of IS NOT NULL
), a AS (
 SELECT segment_id,ts,avg(speed) speed,avg(travel_time) travel_time,count(*) observations
 FROM x GROUP BY 1,2
), f AS (
 SELECT segment_id, percentile_cont(.95) WITHIN GROUP (ORDER BY speed) free_flow_speed
 FROM a GROUP BY 1
)
SELECT a.*,f.free_flow_speed,GREATEST(0,LEAST(1,1-a.speed/NULLIF(f.free_flow_speed,0)))
FROM a JOIN f USING(segment_id)
ON CONFLICT (segment_id,ts) DO UPDATE SET speed=EXCLUDED.speed,travel_time=EXCLUDED.travel_time,observations=EXCLUDED.observations,free_flow_speed=EXCLUDED.free_flow_speed,congestion_index=EXCLUDED.congestion_index;

INSERT INTO analytics.fact_traffic_hourly
SELECT segment_id,date_trunc('hour',ts),avg(speed),avg(travel_time),sum(observations),max(free_flow_speed),
       GREATEST(0,LEAST(1,1-avg(speed)/NULLIF(max(free_flow_speed),0)))
FROM analytics.fact_traffic_15min
GROUP BY segment_id,date_trunc('hour',ts)
ON CONFLICT (segment_id,ts) DO UPDATE SET speed=EXCLUDED.speed,travel_time=EXCLUDED.travel_time,observations=EXCLUDED.observations,free_flow_speed=EXCLUDED.free_flow_speed,congestion_index=EXCLUDED.congestion_index;

INSERT INTO analytics.fact_trips_hourly
SELECT pu_location_id,do_location_id,date_trunc('hour',pickup_ts),
       count(*),avg(EXTRACT(EPOCH FROM(dropoff_ts-pickup_ts))/60.0),avg(trip_distance),
       avg(fare_amount),sum(fare_amount),sum(tip_amount),sum(COALESCE(cbd_congestion_fee,0))
FROM staging.tlc_yellow
WHERE pickup_ts IS NOT NULL AND dropoff_ts>pickup_ts AND trip_distance>=0
GROUP BY 1,2,3
ON CONFLICT (pickup_zone_id,dropoff_zone_id,hour_local) DO UPDATE SET trip_count=EXCLUDED.trip_count;

INSERT INTO analytics.hourly_traffic_enriched
SELECT t.segment_id,t.ts,t.speed,t.travel_time,t.observations,t.free_flow_speed,t.congestion_index,
       w.temperature_2m,w.relative_humidity_2m,w.apparent_temperature,w.precipitation,w.rain,w.snowfall,w.weather_code,w.cloud_cover,w.wind_speed_10m,w.wind_gusts_10m,
       COALESCE(i.incident_count,0),COALESCE(i.persons_injured,0),COALESCE(i.persons_killed,0),COALESCE(i.severity_score,0),
       COALESCE(tr.trip_count,0),tr.avg_duration_min,tr.avg_distance_miles,tr.avg_fare,tr.total_fare,tr.total_tip,tr.total_congestion_fee
FROM analytics.fact_traffic_hourly t
LEFT JOIN clean.dim_weather w ON w.ts_local=(t.ts AT TIME ZONE 'America/New_York')
LEFT JOIN (
 SELECT date_trunc('hour',ts_local) ts_local,count(*) incident_count,sum(persons_injured) persons_injured,sum(persons_killed) persons_killed,sum(severity_score) severity_score
 FROM analytics.fact_incidents GROUP BY 1
) i ON i.ts_local=(t.ts AT TIME ZONE 'America/New_York')
LEFT JOIN (
 SELECT hour_local,sum(trip_count) trip_count,avg(avg_duration_min) avg_duration_min,avg(avg_distance_miles) avg_distance_miles,
        avg(avg_fare) avg_fare,sum(total_fare) total_fare,sum(total_tip) total_tip,sum(total_congestion_fee) total_congestion_fee
 FROM analytics.fact_trips_hourly GROUP BY 1
) tr ON tr.hour_local=(t.ts AT TIME ZONE 'America/New_York')
ON CONFLICT (segment_id,ts) DO UPDATE SET speed=EXCLUDED.speed,temperature_2m=EXCLUDED.temperature_2m,trip_count=EXCLUDED.trip_count;
