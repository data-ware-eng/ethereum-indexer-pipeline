import logging
import re
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

API_URL = "https://dummyjson.com/users?limit=30"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log", encoding="utf-8")
    ]
)

SUSPICIOUS_PATTERN = re.compile(
    r"DROP\s+TABLE|UNION\s+SELECT|DELETE\s+FROM|<script|;--",
    re.IGNORECASE,
)


def contains_suspicious_text(value: object) -> bool:
    """Detect potentially malicious text patterns."""

    if pd.isna(value):
        return False

    return bool(SUSPICIOUS_PATTERN.search(str(value)))


def flag_suspicious_rows(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Flag suspicious records."""

    text_columns = df.select_dtypes(
        include=["object", "string"]
    ).columns

    df["is_suspicious"] = False

    for column in text_columns:
        df["is_suspicious"] |= df[column].apply(
            contains_suspicious_text
        )

    return df


def extract_customers() -> None:
    """Extract customers from DummyJSON."""

    logging.info("Starting extraction")

    response = requests.get(
        API_URL,
        timeout=20,
    )

    response.raise_for_status()

    users = response.json().get(
        "users",
        []
    )

    df = pd.DataFrame(users)

    df = flag_suspicious_rows(df)

    output_file = (
        RAW_DIR / "customers_raw.csv"
    )

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8",
    )

    logging.info(
        "Extracted %s customer records",
        len(df),
    )


if __name__ == "__main__":
    extract_customers()