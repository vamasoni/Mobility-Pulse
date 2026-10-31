# MobilityPulse runbook

1. Configure `.env` from `.env.example`.
2. Start services: `docker compose up -d --build postgres mlflow dashboard`.
3. Run pipeline: `docker compose --profile pipeline run --rm app`.
4. Optional orchestration: `docker compose --profile airflow up -d --build airflow`; trigger `mobilitypulse_end_to_end` manually.
5. Inspect row counts and model metrics before interpreting the dashboard.

Never run two full ingestion jobs concurrently. Full ingestion currently truncates and reloads raw tables. The pipeline is not yet incremental.
