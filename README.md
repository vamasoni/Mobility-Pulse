# MobilityPulse — End-to-End Mobility Analytics Platform

MobilityPulse is a clean, reproducible NYC mobility analytics project covering data engineering, analytics, forecasting, anomaly detection, clustering, root-cause analysis, and an interactive dashboard.

## Scope

- Manhattan
- January–May 2026 by default
- NYC DOT Traffic Speeds
- NYC TLC Yellow Taxi
- NYC Motor Vehicle Collisions
- Open-Meteo hourly weather
- OpenStreetMap road network

## Architecture

NYC APIs/files → Python ingestion → raw filesystem + optional MinIO/S3 → PostgreSQL/PostGIS (`raw → staging → clean → analytics`) → dbt/tests → ML → MLflow → Streamlit/Power BI-ready analytics.

## Clean-start principle

This repository intentionally has one configuration source: `.env`.

PostgreSQL credentials are passed to Docker Compose and Python from the same `.env`, eliminating the credential drift that commonly happens when containers and local Python use different passwords.

## Quick start

```powershell
copy .env.example .env
docker compose down -v
docker compose up -d postgres postgis-init minio
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/check_connection.py
```

Then initialize the warehouse:

```powershell
python scripts/init_db.py
```

Run ingestion:

```powershell
python -m ingestion.run_all
```

Build analytics:

```powershell
python scripts/build_analytics.py
```

Build ML features and models:

```powershell
python ml/build_features.py
python ml/forecast.py
python ml/forecast_xgb.py
python ml/anomaly.py
python ml/clustering.py
python ml/root_cause.py
python ml/monitor.py
```

Run the dashboard:

```powershell
streamlit run dashboards/app.py
```

MLflow:

```powershell
docker compose --profile mlflow up -d mlflow
```

## Notes

The raw layer is local by default for fast development. `storage/s3.py` provides the MinIO/S3 adapter required by the architecture. The project can be switched to S3 with configuration rather than rewriting ingestion code.

Kafka, Spark, and deep learning are deliberately excluded from the first finished version, as recommended by the project scope.
