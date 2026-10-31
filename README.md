# MobilityPulse — Docker-first NYC mobility analytics

## Architecture
PostgreSQL/PostGIS stores raw, staging, clean and analytics schemas. The app image contains ingestion, SQL/feature engineering, ML and Streamlit dependencies. Airflow (optional profile) orchestrates the same Python modules. MLflow tracks experiments. Local `data/` and `models/` are bind-mounted; database and MLflow state use named volumes.

## Prerequisites
- Docker Desktop with Compose v2 and sufficient memory/disk for Parquet and model training.
- NYC source data is downloaded by `ingestion.run_all`; this requires network access and Socrata/TLC endpoints to provide the configured date range.
- Copy `.env.example` to `.env` and set a strong `POSTGRES_PASSWORD`.

## Start infrastructure and dashboard
```powershell
Copy-Item .env.example .env
# Edit .env and set POSTGRES_PASSWORD
docker compose up -d --build postgres mlflow dashboard
```
Open http://localhost:8501. The dashboard intentionally displays diagnostic empty states before analytics data exists.

## Run the complete pipeline inside Docker
```powershell
docker compose --profile pipeline run --rm app
```
This initializes the schema, downloads/extracts source data, loads raw tables, builds analytics and features, trains LightGBM, and runs anomaly/clustering/monitoring stages. It can take a long time for multi-month TLC data. Do not launch duplicate runs concurrently.

## Optional Airflow orchestration
```powershell
docker compose --profile airflow up -d --build airflow
```
Open http://localhost:8080. Airflow standalone creates the admin account; retrieve its initial password from the container logs. The `mobilitypulse_end_to_end` DAG is manual-triggered. It initializes the database and downloads sources before loading and transforming them.

## MLflow
Open http://localhost:5000. Tracking uses a persistent SQLite backend and artifact proxy in the MLflow container.

## Important data semantics
- All traffic fact timestamps are stored as `timestamptz` instants. The current SQL interprets DOT `data_as_of` as America/New_York local wall time. Verify this against the live source metadata before relying on time-of-day analysis; change only if the endpoint supplies UTC or explicit offsets.
- TLC pickup/dropoff and Open-Meteo hourly timestamps are treated as New York local wall time.
- Incident records without a borough are excluded from the Manhattan subset. Invalid (0,0) coordinates are retained as null geometry, not a point at Null Island.
- Current taxi/incident enrichment remains citywide/hourly, not road-segment-specific. Do not interpret it as a causal or segment-level relationship.
- Free-flow speed is currently estimated from the full available traffic history. Treat model evaluation as exploratory until a leakage-safe training-only free-flow reference is implemented.

## Validation and limitations
Run `python -m compileall -q .` and `pytest -q` inside the app image for basic checks. The code has not been executed against your actual Postgres instance or full NYC source data in this environment. Forecast accuracy, source endpoint historical coverage, and DOT timestamp semantics must be verified on your machine. LightGBM evaluation uses a chronological timestamp split and reports persistence, previous-day and previous-week baselines; it is not a hyperparameter-tuned production model.

## Useful commands
```powershell
docker compose ps
docker compose logs --tail=100 postgres mlflow dashboard
docker compose exec postgres psql -U mobility -d mobilitypulse
```
