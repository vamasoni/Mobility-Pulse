# Clean Runbook

1. Copy `.env.example` to `.env`.
2. If this is a true reset of the old project, stop the old containers and remove the old volume:
   `docker compose down -v`
   If the old container was created outside this compose file, remove it once with `docker rm -f mobilitypulse-postgres`.
3. Start PostgreSQL/PostGIS and MinIO:
   `docker compose up -d postgres minio`
4. Create the virtual environment and install `requirements.txt`.
5. `python scripts/check_connection.py`
6. `python scripts/init_db.py`
7. `python -m ingestion.run_all`
8. `python scripts/load_sources.py`
9. `python scripts/build_analytics.py`
10. `python ml/build_features.py`
11. `python ml/forecast.py`
12. `python ml/forecast_xgb.py`
13. `python ml/anomaly.py`
14. `python ml/clustering.py`
15. `python ml/root_cause.py`
16. `python ml/monitor.py`
17. `streamlit run dashboards/app.py`

Run each stage separately the first time. Once validated, the same commands can be placed behind an Airflow DAG.
