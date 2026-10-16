from datetime import datetime
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.providers.standard.operators.python import PythonOperator

default_args = {
    "owner": "data_engineering",
    "retries": 1,
}

with DAG(
    dag_id="ethereum_indexer_pipeline_v1",
    default_args=default_args,
    description="Ethereum Indexer Pipeline on Docker",
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["blockchain", "etl"],
) as dag:

# Import your pipeline function from transform.py
 from src.transform import run as run_etl_pipeline

run_etl = PythonOperator(
    task_id="execute_ethereum_indexer",
    python_callable=run_etl_pipeline
)

run_etl