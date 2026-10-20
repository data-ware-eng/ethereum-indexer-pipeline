from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator


default_args = {
    "owner": "data_engineering",
    "retries": 1,
}


def run_etl_pipeline():
    """
    Execute the complete ETL pipeline.

    Step 1:
    Extract customer data from the API and save it
    into the raw data layer.

    Step 2:
    Execute the transformation layer using the
    newly generated raw CSV file.
    """

    from src.extract import extract_customers
    from src.transform import run

    # Extract raw customer data
    extract_customers()

    # Transform and process the extracted data
    run()


with DAG(
    dag_id="ethereum_indexer_pipeline_v1",
    default_args=default_args,
    description="Customer ETL Pipeline",
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["etl", "customers"],
) as dag:

    run_etl = PythonOperator(
        task_id="execute_ethereum_indexer",
        python_callable=run_etl_pipeline,
    )

    run_etl