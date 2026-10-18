import pandas as pd
import sqlite3


JOBS_DB = "job_postings/jobs.db"


def load_excel_file(filepath: str):
    sheets = {}
    with pd.ExcelFile(filepath) as xls:
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            sheets[sheet_name] = df.reset_index()
    return sheets


def save_jobs(jobs: pd.DataFrame, db_path: str = JOBS_DB, table: str = "jobs") -> int:
    if jobs.empty:
        return 0

    rows = jobs.copy()
    for column in rows.columns:
        if rows[column].map(lambda v: isinstance(v, (list, tuple, set, dict))).any():
            rows[column] = rows[column].map(lambda v: ", ".join(map(str, v))
                                            if isinstance(v, (list, tuple, set)) else v)
    rows = rows.astype(object).where(pd.notna(rows), None)
    connection = sqlite3.connect(db_path)
    
    try:
        columns = list(rows.columns)
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {table} ("
            + ", ".join(f'"{c}"' for c in columns)
            + ', PRIMARY KEY ("site", "id"))'
        )
        existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        for column in columns:
            if column not in existing:
                connection.execute(f'ALTER TABLE {table} ADD COLUMN "{column}"')

        placeholders = ", ".join("?" * len(columns))
        connection.executemany(
            f"INSERT OR REPLACE INTO {table} ("
            + ", ".join(f'"{c}"' for c in columns)
            + f") VALUES ({placeholders})",
            rows.itertuples(index=False, name=None),
        )
        connection.commit()
        return len(rows)
    finally:
        connection.close()