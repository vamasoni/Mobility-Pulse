# Code revision notes and validation boundary

## Addressed in this revision
- Dashboard chart uses the actual `hour_of_day` view field and renders diagnostic/empty states instead of stopping before layout.
- Forecast chart is filtered to one selected segment rather than drawing all segments as one line.
- Dashboard joins segment and taxi-zone labels when dimension records exist.
- TLC loader reads bounded PyArrow batches and writes using PostgreSQL COPY; per-row SHA1 calculation was removed. The raw row_hash column remains nullable for schema compatibility and is not used downstream.
- TLC module imports `Path`.
- Pipeline order now initializes the schema, extracts/downloads sources, loads raw tables, builds analytics/features, then trains/detects/clusters.
- Feature engineering reindexes each segment to an hourly UTC grid before constructing time-based lags and target.
- Forecast evaluation uses one global chronological cutoff and reports persistence, previous-day and previous-week baselines; forecast_ts is target hour (origin + 1h).
- Monitoring inserts a non-null run_ts.
- (0,0) collision coordinates become null geometry; records without borough are not discarded by the transform SQL if present in raw data.
- Unused OSM/dbt artifacts and stale committed model artifact removed; XGBoost script removed pending a fair unified comparison implementation.
- Docker services include PostgreSQL/PostGIS, MLflow, a dashboard, an on-demand pipeline runner and optional Airflow.

## Known limitations; do not over-interpret
- DOT `data_as_of` is currently interpreted as America/New_York local wall time. Confirm the endpoint's actual timestamp contract against live API metadata before trusting hour-of-day joins. If the API emits UTC or offset-aware values, revise the conversion accordingly.
- `clean.dim_segment.geom` and `clean.dim_zone.geom` are not populated by this revision. Names are populated from available lookup/source attributes, but spatial segment-to-zone joins are not implemented. Trip and incident enrichments remain citywide/hourly and must not be described as segment-specific or causal.
- Free-flow speed is still derived from the full observed history in the SQL transformation. That can leak test-period information into the congestion feature. Treat model metrics as exploratory until free-flow references are estimated from training-only history.
- The LightGBM model is a baseline model, not hyperparameter tuned or cross-validated. Model accuracy cannot be asserted without the user's actual dataset.
- XGBoost was removed rather than retain an implementation with inconsistent outputs. Add it back only in a shared comparison runner with identical train/test timestamps, baselines and prediction persistence.
- DOT extractor still needs endpoint-level validation for historical coverage, field selection, pagination completeness and empty-day retry behavior. Do not assume Jan-May 2026 coverage is available merely because date bounds are configured.
- Collision extraction currently requests Manhattan borough records. Records with null borough cannot be recovered by that borough-filtered source query; the SQL transform no longer independently discards null-borough rows already present in raw.
- Airflow image build and full end-to-end runtime have not been executed in this environment. Only Python compilation, unit tests and Compose YAML parsing were performed.
- Full database migrations, SQL execution, PostgreSQL COPY throughput, Docker health checks and model training require Docker/PostGIS and the real input datasets.
