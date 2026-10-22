# Architecture

Extractors are intentionally separated from transformations.

Raw:
- DOT JSONL
- TLC monthly Parquet
- collisions JSONL
- weather JSON
- OSM GraphML/GeoJSON

Warehouse:
- raw: source-shaped data
- staging: typed data
- clean: validated/reference dimensions
- analytics: facts, enriched hourly table, ML tables

ML:
- seasonal-naive baseline
- LightGBM
- XGBoost benchmark
- rule + Isolation Forest anomalies
- KMeans daily/hourly speed profiles
- root-cause comparison
- monitoring table

Serving:
- Streamlit dashboard
- MLflow experiment tracking
- dbt models/tests
