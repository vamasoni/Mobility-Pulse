CREATE OR REPLACE VIEW analytics.v_kpis AS
SELECT
    count(DISTINCT segment_id) AS segments,
    count(*) AS hourly_rows,
    avg(speed) AS avg_speed,
    avg(congestion_index) AS avg_congestion,
    max(speed) AS max_speed
FROM analytics.fact_traffic_hourly;

CREATE OR REPLACE VIEW analytics.v_congestion_by_hour AS
SELECT
    extract(hour FROM (ts AT TIME ZONE 'America/New_York'))::int AS hour_of_day,
    avg(speed) AS avg_speed,
    avg(congestion_index) AS avg_congestion
FROM analytics.fact_traffic_hourly
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE VIEW analytics.v_top_congested_segments AS
SELECT
    segment_id,
    avg(congestion_index) AS avg_congestion,
    avg(speed) AS avg_speed,
    count(*) AS observations
FROM analytics.fact_traffic_hourly
GROUP BY 1
ORDER BY avg_congestion DESC
LIMIT 20;

CREATE OR REPLACE VIEW analytics.v_od_flows AS
SELECT
    pickup_zone_id,
    dropoff_zone_id,
    sum(trip_count) AS trips
FROM analytics.fact_trips_hourly
GROUP BY 1, 2
ORDER BY trips DESC;
