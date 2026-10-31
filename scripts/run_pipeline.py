"""Run the complete MobilityPulse pipeline in dependency order."""
from __future__ import annotations
import argparse, subprocess, sys
STAGES=[("Initialize database","scripts.init_db"),("Extract/download source datasets","ingestion.run_all"),("Load raw source data","scripts.load_sources"),("Build analytics","scripts.build_analytics"),("Build ML features","ml.build_features"),("Train/evaluate LightGBM","ml.forecast"),("Detect anomalies","ml.anomaly"),("Cluster segments","ml.clustering"),("Congestion driver analysis","ml.root_cause"),("Model monitoring","ml.monitor")]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--skip-ml",action="store_true"); args=parser.parse_args()
    stages=STAGES[:5] if args.skip_ml else STAGES
    for label,module in stages:
        print(f"\n===== {label} =====",flush=True)
        subprocess.run([sys.executable,"-m",module],check=True)
    print("Pipeline completed.")
if __name__=="__main__": main()
