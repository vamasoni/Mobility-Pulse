from __future__ import annotations
import os, uuid
import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from lightgbm import LGBMRegressor
from db import connect, executemany
from config import MODEL_DIR

FEATURES=["hour","dow","is_holiday","speed","lag_1","lag_24","lag_168","rolling_6","congestion_index","trip_count","incident_count","temperature_2m","precipitation","wind_speed_10m"]

def main() -> None:
    with connect() as conn: df=pd.read_sql("SELECT * FROM analytics.ml_features ORDER BY ts, segment_id",conn)
    if len(df)<100: raise RuntimeError(f"Need >=100 feature rows; found {len(df)}")
    df["ts"]=pd.to_datetime(df["ts"],utc=True)
    df=df.replace([float("inf"),float("-inf")],float("nan")).dropna(subset=FEATURES+["target_speed"])
    split_time=df["ts"].quantile(.8)
    train=df["ts"]<split_time; test=~train
    if train.sum()<50 or test.sum()<10: raise RuntimeError("Insufficient chronological train/test rows")
    model=LGBMRegressor(n_estimators=500,learning_rate=.03,num_leaves=31,max_depth=-1,subsample=.85,colsample_bytree=.85,reg_lambda=1.0,random_state=42,verbosity=-1,n_jobs=-1)
    model.fit(df.loc[train,FEATURES],df.loc[train,"target_speed"])
    pred=model.predict(df.loc[test,FEATURES]); y=df.loc[test,"target_speed"].to_numpy()
    test_df=df.loc[test].copy()
    baselines={"persistence":test_df["speed"].to_numpy(),"previous_day":test_df["lag_24"].to_numpy(),"previous_week":test_df["lag_168"].to_numpy()}
    metrics={"mae":float(mean_absolute_error(y,pred)),"rmse":float(mean_squared_error(y,pred)**.5)}
    for name,values in baselines.items(): metrics[name+"_mae"]=float(mean_absolute_error(y,values))
    run_id=str(uuid.uuid4()); MODEL_DIR.mkdir(parents=True,exist_ok=True)
    joblib.dump({"model":model,"features":FEATURES,"model_name":"lightgbm_next_hour","split_time":str(split_time)},MODEL_DIR/"lightgbm_forecaster.joblib")
    out=test_df[["segment_id","ts","target_speed"]].copy(); out["forecast_ts"]=out["ts"]+pd.Timedelta(hours=1); out["predicted_speed"]=pred
    out["abs_error"]=(out.target_speed-pred).abs(); out["sq_error"]=(out.target_speed-pred)**2
    with connect() as conn:
        conn.execute("DELETE FROM analytics.ml_predictions WHERE model_run_id=%s",(run_id,))
        executemany(conn,"INSERT INTO analytics.ml_predictions(segment_id,ts,forecast_ts,predicted_speed,actual_speed,abs_error,sq_error,model_run_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",[(int(r.segment_id),r.ts.to_pydatetime(),r.forecast_ts.to_pydatetime(),float(r.predicted_speed),float(r.target_speed),float(r.abs_error),float(r.sq_error),run_id) for r in out.itertuples(index=False)])
        conn.execute("INSERT INTO analytics.ml_monitoring(run_ts,model_name,mae,rmse,baseline_mae,drift_flag) VALUES (now(),'lightgbm',%s,%s,%s,%s)",(metrics["mae"],metrics["rmse"],metrics["persistence_mae"],metrics["mae"]>metrics["persistence_mae"]))
    try:
        import mlflow
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI","http://mlflow:5000"))
        with mlflow.start_run(run_name="lightgbm_next_hour"):
            mlflow.log_metrics(metrics); mlflow.log_params({"model":"LightGBM","features":len(FEATURES),"train_rows":int(train.sum()),"test_rows":int(test.sum())}); mlflow.log_artifact(str(MODEL_DIR/"lightgbm_forecaster.joblib"))
    except Exception as exc: print(f"MLflow logging warning: {exc}")
    print({"model":"LightGBM","split_time":str(split_time),**metrics,"test_rows":int(test.sum())})

if __name__ == "__main__": main()
