from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_dashboard_uses_actual_hour_view_column():
    text = (ROOT / "dashboards" / "app.py").read_text()
    assert 'x="hour_of_day"' in text
    assert 'x="hour", y="avg_congestion"' not in text

def test_forecast_uses_next_hour_timestamp_and_persistence_baseline():
    text = (ROOT / "ml" / "forecast.py").read_text()
    assert 'pd.Timedelta(hours=1)' in text
    assert '"persistence"' in text

def test_pipeline_initializes_and_extracts_before_loading():
    text = (ROOT / "scripts" / "run_pipeline.py").read_text()
    assert text.index('"scripts.init_db"') < text.index('"ingestion.run_all"') < text.index('"scripts.load_sources"')
