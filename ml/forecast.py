from __future__ import annotations
import uuid
import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from lightgbm import LGBMRegressor
from db import connect, executemany
from config import MODEL_DIR

FEATURES = ["hour", "dow", "is_holiday", "lag_1", "lag_24", "lag_168", "rolling_6", "congestion_index", "trip_count", "incident_count", "temperature_2m", "precipitation", "wind_speed_10m"]

def main() -> None:
    with connect() as conn:
        df = pd.read_sql("SELECT * FROM analytics.ml_features ORDER BY ts", conn)
    if len(df) < 100:
        print(f"Need at least 100 feature rows to train; found {len(df)}. Skipping forecast.")
        return
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.replace([float("inf"), float("-inf")], float("nan")).dropna(subset=FEATURES + ["target_speed", "lag_168"])
    split = df["ts"].quantile(0.8)
    train = df["ts"] < split
    test = ~train
    if train.sum() < 50 or test.sum() < 10:
        print("Not enough distinct time points for a chronological train/test split.")
        return
    model = LGBMRegressor(n_estimators=300, learning_rate=0.04, num_leaves=31, random_state=42, verbosity=-1)
    model.fit(df.loc[train, FEATURES], df.loc[train, "target_speed"])
    pred = model.predict(df.loc[test, FEATURES])
    y = df.loc[test, "target_speed"].to_numpy()
    mae = float(mean_absolute_error(y, pred))
    rmse = float(mean_squared_error(y, pred) ** 0.5)
    baseline = float(mean_absolute_error(y, df.loc[test, "lag_168"].to_numpy()))
    run_id = str(uuid.uuid4())
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_DIR / "lightgbm_forecaster.joblib")
    output = df.loc[test, ["segment_id", "ts", "target_speed"]].copy()
    output["predicted_speed"] = pred
    output["abs_error"] = (output["target_speed"] - pred).abs()
    output["sq_error"] = (output["target_speed"] - pred) ** 2
    with connect() as conn:
        conn.execute("DELETE FROM analytics.ml_predictions")
        executemany(conn, 
            "INSERT INTO analytics.ml_predictions(segment_id,ts,forecast_ts,predicted_speed,actual_speed,abs_error,sq_error,model_run_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            [(int(r.segment_id), r.ts.to_pydatetime(), r.ts.to_pydatetime(), float(r.predicted_speed), float(r.target_speed), float(r.abs_error), float(r.sq_error), run_id) for r in output.itertuples(index=False)],
        )
    try:
        import mlflow
        mlflow.set_tracking_uri(__import__("os").getenv("MLFLOW_TRACKING_URI", "file:./mlruns"))
        with mlflow.start_run(run_name="lightgbm_next_hour"):
            mlflow.log_metrics({"mae": mae, "rmse": rmse, "seasonal_naive_mae": baseline})
            mlflow.log_params({"model": "LightGBM", "n_estimators": 300, "train_rows": int(train.sum()), "test_rows": int(test.sum())})
    except ImportError:
        pass  # MLflow is an optional dependency; model training does not depend on it.
    print({"MAE": mae, "RMSE": rmse, "seasonal_naive_MAE": baseline, "test_rows": int(test.sum())})

if __name__ == "__main__":
    main()
