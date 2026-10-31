from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator
PROJECT="/opt/mobility-pulse"
def cmd(task_id,module):
    return BashOperator(task_id=task_id,bash_command=f"cd {PROJECT} && export PYTHONPATH={PROJECT}:$PYTHONPATH && python -u -m {module}",append_env=True)
with DAG(dag_id="mobilitypulse_end_to_end",start_date=datetime(2026,1,1),schedule=None,catchup=False,max_active_runs=1,tags=["mobilitypulse","etl","ml"]) as dag:
    init=cmd("initialize_database","scripts.init_db")
    extract=cmd("extract_source_data","ingestion.run_all")
    load=cmd("load_raw_sources","scripts.load_sources")
    analytics=cmd("build_analytics","scripts.build_analytics")
    features=cmd("build_ml_features","ml.build_features")
    lightgbm=cmd("train_lightgbm","ml.forecast")
    anomaly=cmd("detect_anomalies","ml.anomaly")
    cluster=cmd("cluster_segments","ml.clustering")
    root_cause=cmd("congestion_driver_analysis","ml.root_cause")
    monitor=cmd("monitor_models","ml.monitor")
    init >> extract >> load >> analytics >> features
    features >> [lightgbm,anomaly,cluster,root_cause]
    [lightgbm,anomaly,cluster,root_cause] >> monitor
