CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS clean;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS raw.dot_traffic (
    source_date date NOT NULL,
    payload jsonb NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS staging.dot_traffic (
    id bigint,
    speed double precision,
    travel_time double precision,
    status integer,
    data_as_of timestamptz,
    link_id bigint,
    link_points text,
    encoded_poly_line text,
    encoded_poly_line_lvls text,
    owner text,
    transcom_id bigint,
    borough text,
    link_name text,
    source_date date NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.tlc_yellow (
    pickup_ts text,
    dropoff_ts text,
    passenger_count double precision,
    trip_distance double precision,
    ratecode_id double precision,
    store_and_fwd_flag text,
    pu_location_id integer,
    do_location_id integer,
    payment_type integer,
    fare_amount double precision,
    extra double precision,
    mta_tax double precision,
    tip_amount double precision,
    tolls_amount double precision,
    improvement_surcharge double precision,
    total_amount double precision,
    congestion_surcharge double precision,
    airport_fee double precision,
    cbd_congestion_fee double precision,
    source_month date,
    row_hash bigint
);

CREATE TABLE IF NOT EXISTS staging.tlc_yellow (
    pickup_ts timestamp without time zone,
    dropoff_ts timestamp without time zone,
    passenger_count double precision,
    trip_distance double precision,
    pu_location_id integer,
    do_location_id integer,
    fare_amount double precision,
    tip_amount double precision,
    total_amount double precision,
    congestion_surcharge double precision,
    cbd_congestion_fee double precision,
    source_month date,
    row_hash bigint
);

CREATE TABLE IF NOT EXISTS raw.collisions (
    collision_id bigint,
    crash_date text,
    crash_time text,
    borough text,
    latitude double precision,
    longitude double precision,
    persons_injured integer,
    persons_killed integer,
    raw_payload jsonb,
    loaded_at timestamptz default now()
);

CREATE TABLE IF NOT EXISTS staging.collisions (
    incident_id bigint PRIMARY KEY,
    ts_local timestamp,
    borough text,
    latitude double precision,
    longitude double precision,
    persons_injured integer,
    persons_killed integer,
    geom geometry(Point,4326)
);

CREATE TABLE IF NOT EXISTS raw.weather (
    ts_local timestamp,
    temperature_2m double precision,
    relative_humidity_2m double precision,
    apparent_temperature double precision,
    precipitation double precision,
    rain double precision,
    snowfall double precision,
    weather_code integer,
    cloud_cover double precision,
    wind_speed_10m double precision,
    wind_gusts_10m double precision
);

CREATE TABLE IF NOT EXISTS clean.dim_weather (
    ts_local timestamp PRIMARY KEY,
    temperature_2m double precision,
    relative_humidity_2m double precision,
    apparent_temperature double precision,
    precipitation double precision,
    rain double precision,
    snowfall double precision,
    weather_code integer,
    cloud_cover double precision,
    wind_speed_10m double precision,
    wind_gusts_10m double precision,
    loaded_at timestamptz default now()
);

CREATE TABLE IF NOT EXISTS raw.taxi_zone_lookup (
    location_id integer,
    borough text,
    zone text,
    service_zone text
);

CREATE TABLE IF NOT EXISTS clean.dim_zone (
    location_id integer PRIMARY KEY,
    borough text,
    zone text,
    service_zone text,
    geom geometry(MultiPolygon,4326)
);

CREATE TABLE IF NOT EXISTS clean.dim_segment (
    segment_id bigint PRIMARY KEY,
    link_name text,
    owner text,
    geom geometry(Geometry,4326)
);

CREATE TABLE IF NOT EXISTS analytics.fact_traffic_15min (
    segment_id bigint,
    ts timestamptz,
    speed double precision,
    travel_time double precision,
    observations bigint,
    free_flow_speed double precision,
    congestion_index double precision,
    PRIMARY KEY(segment_id, ts)
);

CREATE TABLE IF NOT EXISTS analytics.fact_traffic_hourly (
    segment_id bigint,
    ts timestamptz,
    speed double precision,
    travel_time double precision,
    observations bigint,
    free_flow_speed double precision,
    congestion_index double precision,
    PRIMARY KEY(segment_id, ts)
);

CREATE TABLE IF NOT EXISTS analytics.fact_trips_hourly (
    pickup_zone_id integer,
    dropoff_zone_id integer,
    hour_local timestamp,
    trip_count bigint,
    avg_duration_min double precision,
    avg_distance_miles double precision,
    avg_fare double precision,
    total_fare double precision,
    total_tip double precision,
    total_congestion_fee double precision,
    PRIMARY KEY(pickup_zone_id, dropoff_zone_id, hour_local)
);

CREATE TABLE IF NOT EXISTS analytics.fact_incidents (
    incident_id bigint PRIMARY KEY,
    ts_local timestamp,
    borough text,
    latitude double precision,
    longitude double precision,
    severity_level text,
    severity_score integer,
    persons_injured integer,
    persons_killed integer,
    geom geometry(Point,4326)
);

CREATE TABLE IF NOT EXISTS analytics.hourly_traffic_enriched (
    segment_id bigint,
    ts timestamptz,
    speed double precision,
    travel_time double precision,
    observations bigint,
    free_flow_speed double precision,
    congestion_index double precision,
    temperature_2m double precision,
    relative_humidity_2m double precision,
    apparent_temperature double precision,
    precipitation double precision,
    rain double precision,
    snowfall double precision,
    weather_code integer,
    cloud_cover double precision,
    wind_speed_10m double precision,
    wind_gusts_10m double precision,
    incident_count bigint,
    persons_injured bigint,
    persons_killed bigint,
    incident_severity_score bigint,
    trip_count bigint,
    avg_duration_min double precision,
    avg_distance_miles double precision,
    avg_fare double precision,
    total_fare double precision,
    total_tip double precision,
    total_congestion_fee double precision,
    PRIMARY KEY(segment_id, ts)
);

CREATE TABLE IF NOT EXISTS analytics.ml_features (
    segment_id bigint,
    ts timestamptz,
    speed double precision,
    congestion_index double precision,
    trip_count double precision,
    incident_count double precision,
    temperature_2m double precision,
    precipitation double precision,
    wind_speed_10m double precision,
    hour integer,
    dow integer,
    is_holiday integer,
    lag_1 double precision,
    lag_24 double precision,
    lag_168 double precision,
    rolling_6 double precision,
    target_speed double precision,
    PRIMARY KEY(segment_id, ts)
);

CREATE TABLE IF NOT EXISTS analytics.ml_predictions (
    segment_id bigint,
    ts timestamptz,
    forecast_ts timestamptz,
    predicted_speed double precision,
    actual_speed double precision,
    abs_error double precision,
    sq_error double precision,
    model_run_id text
);

CREATE TABLE IF NOT EXISTS analytics.ml_anomalies (
    segment_id bigint,
    ts timestamptz,
    speed double precision,
    congestion_index double precision,
    anomaly_type text,
    anomaly_score double precision,
    PRIMARY KEY(segment_id, ts, anomaly_type)
);

CREATE TABLE IF NOT EXISTS analytics.ml_monitoring (
    run_ts timestamptz,
    model_name text,
    mae double precision,
    rmse double precision,
    baseline_mae double precision,
    drift_flag boolean
);

CREATE TABLE IF NOT EXISTS analytics.data_quality_log (
    check_ts timestamptz default now(),
    check_name text,
    status text,
    metric_value double precision,
    details text
);
