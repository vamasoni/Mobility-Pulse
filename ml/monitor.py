from __future__ import annotations
from db import connect

def main() -> None:
    with connect() as conn:
        row = conn.execute("SELECT count(*), avg(abs_error), sqrt(avg(sq_error)) FROM analytics.ml_predictions").fetchone()
        if not row or row[0] == 0:
            print("No predictions found. Run python -m ml.forecast first.")
            return
        baseline = conn.execute("""
            SELECT avg(abs(p.actual_speed - f.lag_168))
            FROM analytics.ml_predictions p
            JOIN analytics.ml_features f ON f.segment_id=p.segment_id AND f.ts=p.ts
            WHERE f.lag_168 IS NOT NULL
        """).fetchone()[0]
        mae, rmse = row[1], row[2]
        drift = bool(baseline is not None and mae is not None and mae > baseline)
        conn.execute("INSERT INTO analytics.ml_monitoring(model_name,mae,rmse,baseline_mae,drift_flag) VALUES (%s,%s,%s,%s,%s)", ("lightgbm", mae, rmse, baseline, drift))
    print({"MAE": mae, "RMSE": rmse, "baseline_MAE": baseline, "drift_flag": drift})

if __name__ == "__main__":
    main()
