import os
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from notifications import send_slack_alert

# --- Configuration ----------------------------------------------------------

RAW_FILE = Path("data/raw/customers_raw.csv")
PROCESSED_FILE = Path("data/processed/customers_clean.csv")
QUARANTINE_FILE = Path("quarantine/customers_quarantined.csv")

DB_URL = (
    f"postgresql+psycopg2://postgres:{os.getenv('POSTGRES_PASSWORD')}"
    "@localhost:5432/postgres"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log", encoding="utf-8")
    ]
)

# --- Extract ----------------------------------------------------------------

def read_csv() -> pd.DataFrame:
    """Read CSV using common encoding fallbacks."""

    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
        try:
            return pd.read_csv(RAW_FILE, encoding=enc)
        except UnicodeDecodeError:
            pass

    raise ValueError("Unsupported file encoding")


# --- Transform --------------------------------------------------------------

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Apply data cleansing and standardization rules."""

    df.columns = df.columns.str.lower().str.strip()
    df.rename(columns={"id": "customer_id"}, inplace=True)

    text_cols = df.select_dtypes(include=["object", "string"]).columns

    df[text_cols] = df[text_cols].apply(
        lambda col: (
            col.fillna("")
               .astype(str)
               .str.replace(r"[\x00-\x1F\x7F-\x9F]", "", regex=True)
               .str.strip()
        )
    )

    if "customer_id" in df:
        df["customer_id"] = pd.to_numeric(
            df["customer_id"],
            errors="coerce"
        ).astype("Int64")

    return df.replace({np.nan: None, pd.NA: None})


# --- Load -------------------------------------------------------------------

def load(df: pd.DataFrame) -> None:
    """Load dataset into PostgreSQL."""

    with create_engine(DB_URL, pool_pre_ping=True).begin() as conn:
        conn.exec_driver_sql("SET client_encoding TO 'UTF8'")
        df.to_sql(
            "dim_customer",
            conn,
            if_exists="replace",
            index=False,
            chunksize=1000,
            method="multi",
        )


# --- Pipeline ----------------------------------------------------------------

def run() -> None:
    """Execute customer ETL pipeline."""

    try:
        send_slack_alert("Customer ETL started")

        df = read_csv()

        if "is_suspicious" in df:
            suspicious = df[df["is_suspicious"]]

            if not suspicious.empty:
                QUARANTINE_FILE.parent.mkdir(parents=True, exist_ok=True)
                suspicious.to_csv(QUARANTINE_FILE, index=False)

            df = df[~df["is_suspicious"]]

        if df.empty:
            logging.warning("No valid records found")
            return

        df = transform(df).drop(columns=["is_suspicious"], errors="ignore")

        PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(PROCESSED_FILE, index=False, encoding="utf-8")

        load(df)

        logging.info("Customer ETL completed")
        send_slack_alert("Customer ETL completed")

    except Exception as exc:
        logging.exception("Customer ETL failed")
        send_slack_alert(f"Customer ETL failed: {exc}")


if __name__ == "__main__":
    run()