"""Run the database loading, SQL analytics, and optional ML stages in order."""
from __future__ import annotations
import argparse
import subprocess
import sys

STAGES = [
    ("Load raw files into PostgreSQL", "scripts.load_sources"),
    ("Build SQL analytics and KPI views", "scripts.build_analytics"),
    ("Build ML features", "ml.build_features"),
    ("Train LightGBM forecast", "ml.forecast"),
    ("Train XGBoost forecast", "ml.forecast_xgb"),
    ("Detect traffic anomalies", "ml.anomaly"),
    ("Cluster traffic segments", "ml.clustering"),
    ("Summarize congestion drivers", "ml.root_cause"),
    ("Record model monitoring metrics", "ml.monitor"),
]

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-ml", action="store_true", help="only load sources and build SQL analytics")
    args = parser.parse_args()
    stages = STAGES[:2] if args.skip_ml else STAGES
    for label, module in stages:
        print(f"\n{'=' * 12} {label} {'=' * 12}", flush=True)
        result = subprocess.run([sys.executable, "-m", module], check=False)
        if result.returncode != 0:
            raise SystemExit(f"Stage failed: {module} (exit code {result.returncode}). Fix the error above and rerun this command.")
    print("\nPipeline stages completed. Launch the dashboard with: streamlit run dashboards/app.py")

if __name__ == "__main__":
    main()
