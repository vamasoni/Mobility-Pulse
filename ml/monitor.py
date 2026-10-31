from db import connect

def main():
    with connect() as conn:
        row=conn.execute("SELECT count(*),avg(abs_error),sqrt(avg(sq_error)) FROM analytics.ml_predictions").fetchone()
    if not row or not row[0]:
        print("No prediction records available."); return
    print({"prediction_rows":row[0],"mae":row[1],"rmse":row[2],"note":"Persistence-baseline comparison is recorded during model training."})

if __name__ == "__main__": main()
