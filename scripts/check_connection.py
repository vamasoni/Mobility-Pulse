from db import connect

def main() -> None:
    with connect() as conn:
        row = conn.execute("select current_user, current_database(), version()").fetchone()
    print("PostgreSQL connection OK")
    print(row)

if __name__ == "__main__":
    main()
