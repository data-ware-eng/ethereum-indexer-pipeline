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
    f"@{os.getenv('DB_HOST', 'host.DOCKER.internal')}:5432/postgres"
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

import datetime

def load(df: pd.DataFrame) -> None:
    """Load dataset into PostgreSQL using SCD Type 2 logic."""

    hoy = datetime.date.today()

    df = df.copy()
    df["fecha_inicio"] = hoy
    df["fecha_fin"] = datetime.date(9999, 12, 31)
    df["es_activo"] = True

    with create_engine(DB_URL, pool_pre_ping=True).begin() as conn:
        conn.exec_driver_sql("SET client_encoding TO 'UTF8'")

        # 1. If the table does not exist in the database, create it for the first time
        try:
            df_db = pd.read_sql(
                "SELECT * FROM dim_customer WHERE es_activo = true",
                conn
            )
        except Exception:
            df.to_sql(
                "dim_customer",
                conn,
                if_exists="append",
                index=False,
                chunksize=1000,
                method="multi"
            )
            return

        # 2. Identify existing records that have updated information
        df_merge = pd.merge(
            df_db,
            df,
            on="customer_id",
            how="inner",
            suffixes=("_old", "_new")
        )

        # Compare all columns to check if anything has changed
        columnas_comunes = [
            c for c in df.columns
            if c not in [
                "customer_id",
                "fecha_inicio",
                "fecha_fin",
                "es_activo"
            ]
        ]
        # Compare all monitored columns to check if anythings has changed
        cambios = (df_merge[[c + '_old' for c in columnas_comunes]].values !=
                   df_merge[[c + '_new' for c in columnas_comunes]].values).any(axis=1)

        df_cambios = df_merge[cambios]
      

        if not df_cambios.empty:
            customer_ids_a_expirar = (
                df_cambios["customer_id"]
                .drop_duplicates()
                .tolist()
            )

            # Deactivate old records in the database
            conn.exec_driver_sql(
                f"""
                UPDATE dim_customer
                SET es_activo = false,
                    fecha_fin = '{hoy}'
                WHERE customer_id IN (
                    {','.join(map(str, customer_ids_a_expirar))}
                )
                AND es_activo = true
                """
            )

            # Insert the new version with updated data
            df_nuevas_versiones = df[
                df["customer_id"].isin(customer_ids_a_expirar)
            ]

            df_nuevas_versiones.to_sql(
                "dim_customer",
                conn,
                if_exists="append",
                index=False,
                chunksize=1000,
                method="multi"
            )

        # 3. Insert records that are COMPLETELY NEW
        nuevos_customer_ids = (
            set(df["customer_id"])
            - set(df_db["customer_id"])
        )

        if nuevos_customer_ids:
            df_nuevos_registros = df[
                df["customer_id"].isin(nuevos_customer_ids)
            ]

            df_nuevos_registros.to_sql(
                "dim_customer",
                conn,
                if_exists="append",
                index=False,
                chunksize=1000,
                method="multi"
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