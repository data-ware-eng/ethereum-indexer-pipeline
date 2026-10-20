import logging
import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, inspect

from src.notifications import send_slack_alert


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RAW_FILE = Path("data/raw/customers_raw.csv")
PROCESSED_FILE = Path("data/processed/customers_clean.csv")
QUARANTINE_FILE = Path("quarantine/customers_quarantined.csv")

# PostgreSQL connection for local Astro development
DB_URL = (
    "postgresql+psycopg2://postgres:postgres"
    "@postgres:5432/postgres"
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log", encoding="utf-8")
    ]
)


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------

def read_csv() -> pd.DataFrame:
    """
    Read the raw CSV file using common encoding fallbacks.
    """

    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
        try:
            return pd.read_csv(RAW_FILE, encoding=enc)
        except UnicodeDecodeError:
            continue

    raise ValueError("Unsupported file encoding")


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize the dataset before loading.
    """

    df.columns = df.columns.str.lower().str.strip()

    df.rename(
        columns={"id": "customer_id"},
        inplace=True
    )

    text_cols = df.select_dtypes(
        include=["object", "string"]
    ).columns

    df[text_cols] = df[text_cols].apply(
        lambda col: (
            col.fillna("")
            .astype(str)
            .str.replace(
                r"[\x00-\x1F\x7F-\x9F]",
                "",
                regex=True
            )
            .str.strip()
        )
    )

    if "customer_id" in df.columns:
        df["customer_id"] = pd.to_numeric(
            df["customer_id"],
            errors="coerce"
        ).astype("Int64")

    return df.replace(
        {
            np.nan: None,
            pd.NA: None
        }
    )


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load(df: pd.DataFrame) -> None:
    """
    Load data into PostgreSQL using SCD Type 2 logic.
    """

    today = datetime.date.today()

    df = df.copy()

    df["fecha_inicio"] = today
    df["fecha_fin"] = datetime.date(9999, 12, 31)
    df["es_activo"] = True

    engine = create_engine(
        DB_URL,
        pool_pre_ping=True
    )

    with engine.begin() as conn:

        conn.exec_driver_sql(
            "SET client_encoding TO 'UTF8'"
        )

        # -----------------------------------------------------------
        # First execution bootstrap
        # -----------------------------------------------------------

        inspector = inspect(conn)

        if not inspector.has_table("dim_customer"):

            logging.info(
                "dim_customer table not found. Creating initial table."
            )

            df.to_sql(
                "dim_customer",
                conn,
                if_exists="replace",
                index=False,
                chunksize=1000,
                method="multi"
            )

            logging.info(
                "dim_customer created successfully."
            )

            return

        # -----------------------------------------------------------
        # Read active records
        # -----------------------------------------------------------

        df_db = pd.read_sql(
            "SELECT * FROM dim_customer WHERE es_activo = true",
            conn
        )

        # -----------------------------------------------------------
        # Detect record changes
        # -----------------------------------------------------------

        common_columns = [
            c for c in df.columns
            if c not in [
                "customer_id",
                "fecha_inicio",
                "fecha_fin",
                "es_activo"
            ]
        ]

        df_merge = pd.merge(
            df_db,
            df,
            on="customer_id",
            how="inner",
            suffixes=("_old", "_new")
        )

        changes = (
            df_merge[
                [f"{c}_old" for c in common_columns]
            ].values
            !=
            df_merge[
                [f"{c}_new" for c in common_columns]
            ].values
        ).any(axis=1)

        df_changes = df_merge[changes]

        # -----------------------------------------------------------
        # Expire old versions and insert updated versions
        # -----------------------------------------------------------

        if not df_changes.empty:

            customer_ids_to_expire = (
                df_changes["customer_id"]
                .drop_duplicates()
                .tolist()
            )

            conn.exec_driver_sql(
                f"""
                UPDATE dim_customer
                SET es_activo = false,
                    fecha_fin = '{today}'
                WHERE customer_id IN (
                    {",".join(map(str, customer_ids_to_expire))}
                )
                AND es_activo = true
                """
            )

            df_new_versions = df[
                df["customer_id"].isin(
                    customer_ids_to_expire
                )
            ]

            df_new_versions.to_sql(
                "dim_customer",
                conn,
                if_exists="append",
                index=False,
                chunksize=1000,
                method="multi"
            )

        # -----------------------------------------------------------
        # Insert completely new customers
        # -----------------------------------------------------------

        new_customer_ids = (
            set(df["customer_id"])
            - set(df_db["customer_id"])
        )

        if new_customer_ids:

            df_new_records = df[
                df["customer_id"].isin(
                    new_customer_ids
                )
            ]

            df_new_records.to_sql(
                "dim_customer",
                conn,
                if_exists="append",
                index=False,
                chunksize=1000,
                method="multi"
            )

        logging.info(
            "PostgreSQL load completed successfully."
        )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run() -> None:
    """
    Execute the complete ETL process.
    """

    try:

        send_slack_alert(
            "Customer ETL started"
        )

        df = read_csv()

        if "is_suspicious" in df.columns:

         logging.info(
    f"Suspicious records found: {len(df[df['is_suspicious']])}"
)

        suspicious = df[
                df["is_suspicious"]
            ]

        if not suspicious.empty:

                QUARANTINE_FILE.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                suspicious.to_csv(
                    QUARANTINE_FILE,
                    index=False
                )
                send_slack_alert(
    f"⚠️ Security Alert: {len(suspicious)} suspicious records detected and isolated in quarantine."
)

        df = df[
                ~df["is_suspicious"]
            ]

        if df.empty:

            logging.warning(
                "No valid records found."
            )

            return

        df = transform(df)

        df = df.drop(
            columns=["is_suspicious"],
            errors="ignore"
        )

        PROCESSED_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        df.to_csv(
            PROCESSED_FILE,
            index=False,
            encoding="utf-8"
        )

        load(df)

        logging.info(
            "Customer ETL completed successfully."
        )

        send_slack_alert(
            "Customer ETL completed"
        )

    except Exception as exc:

        logging.exception(
            "Customer ETL failed"
        )

        send_slack_alert(
            f"Customer ETL failed: {exc}"
        )


if __name__ == "__main__":
    run()