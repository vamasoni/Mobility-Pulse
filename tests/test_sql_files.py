from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_sql_files_exist():
    for filename in ("00_init.sql", "01_transform.sql", "02_metrics.sql"):
        assert (ROOT / "sql" / filename).is_file()

def test_metrics_views_are_defined():
    sql = (ROOT / "sql" / "02_metrics.sql").read_text(encoding="utf-8")
    for view in ("v_kpis", "v_congestion_by_hour", "v_top_congested_segments", "v_od_flows"):
        assert f"analytics.{view}" in sql

def test_compose_does_not_require_minio():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8").lower()
    assert "minio/minio" not in compose
