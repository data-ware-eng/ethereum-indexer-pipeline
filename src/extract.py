import logging
import re
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Raw data directory configuration
# ---------------------------------------------------------------------------

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# API source configuration
# ---------------------------------------------------------------------------

API_URL = "https://dummyjson.com/users?limit=30"

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            "pipeline.log",
            encoding="utf-8"
        )
    ]
)

# ---------------------------------------------------------------------------
# Security pattern detection
# ---------------------------------------------------------------------------
# Detect common SQL Injection and script injection patterns.
# Records matching these patterns will be flagged and later
# moved to quarantine during the transformation stage.
# ---------------------------------------------------------------------------

SUSPICIOUS_PATTERN = re.compile(
    r"DROP\s+TABLE|UNION\s+SELECT|DELETE\s+FROM|<script|;--",
    re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Security validation functions
# ---------------------------------------------------------------------------

def contains_suspicious_text(value: object) -> bool:
    """
    Detect potentially malicious content.
    """

    if pd.isna(value):
        return False

    return bool(
        SUSPICIOUS_PATTERN.search(str(value))
    )


def flag_suspicious_rows(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Flag rows containing suspicious patterns.
    """

    text_columns = df.select_dtypes(
        include=["object", "string"]
    ).columns

    df["is_suspicious"] = False

    for column in text_columns:

        df["is_suspicious"] |= (
            df[column]
            .apply(contains_suspicious_text)
        )

    return df

# ---------------------------------------------------------------------------
# Extraction process
# ---------------------------------------------------------------------------

def extract_customers() -> None:
    """
    Extract customer data from DummyJSON API.
    """

    logging.info(
        "Starting extraction"
    )

    response = requests.get(
        API_URL,
        timeout=20
    )

    response.raise_for_status()

    users = response.json().get(
        "users",
        []
    )

    df = pd.DataFrame(users)

    # -----------------------------------------------------------------------
    # SECURITY TEST RECORD
    # -----------------------------------------------------------------------
    # This synthetic record simulates a SQL Injection attempt.
    #
    # Expected behavior:
    # 1. Record is flagged as suspicious.
    # 2. Record is moved to quarantine.
    # 3. Record is excluded from PostgreSQL.
    # 4. Slack security alert is triggered.
    #
    # Remove this block after validating the quarantine process.
    # -----------------------------------------------------------------------

    test_record = {
        "id": 999999,
        "firstName": "Security",
        "lastName": "Test",
        "email": "security@test.local",
        "company": "DROP TABLE customers;"
    }

    df = pd.concat(
        [
            df,
            pd.DataFrame([test_record])
        ],
        ignore_index=True
    )

    # -----------------------------------------------------------------------
    # Apply security checks
    # -----------------------------------------------------------------------

    df = flag_suspicious_rows(df)

    output_file = (
        RAW_DIR / "customers_raw.csv"
    )

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8"
    )

    logging.info(
        "Extracted %s customer records",
        len(df)
    )

# ---------------------------------------------------------------------------
# Local execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    extract_customers()