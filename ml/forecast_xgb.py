from __future__ import annotations
import joblib
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from db import connect
from config import MODEL_DIR

FEATURES = ["hour", "dow", "is_holiday", "lag_1", "lag_24", "lag_168", "rolling_6", "congestion_index", "trip_count", "incident_count", "temperature_2m", "precipitation", "wind_speed_10m"]

def main() -> None:
    with connect() as conn:
        df = pd.read_sql("SELECT * FROM analytics.ml_features ORDER BY ts", conn)
    if len(df) < 100:
        print(f"Need at least 100 feature rows to train; found {len(df)}. Skipping XGBoost.")
        return
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.replace([float("inf"), float("-inf")], float("nan")).dropna(subset=FEATURES + ["target_speed"])
    split = df["ts"].quantile(0.8)
    train, test = df["ts"] < split, df["ts"] >= split
    if train.sum() < 50 or test.sum() < 10:
        print("Not enough data for a chronological XGBoost split.")
        return
    model = XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, objective="reg:squarederror", n_jobs=4, random_state=42)
    model.fit(df.loc[train, FEATURES], df.loc[train, "target_speed"])
    prediction = model.predict(df.loc[test, FEATURES])
    y = df.loc[test, "target_speed"]
    print({"MAE": float(mean_absolute_error(y, prediction)), "RMSE": float(mean_squared_error(y, prediction) ** 0.5)})
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_DIR / "xgb_forecaster.joblib")

if __name__ == "__main__":
    main()
