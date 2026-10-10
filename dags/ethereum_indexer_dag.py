from datetime import datetime
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator

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

    run_etl = DockerOperator(
        task_id="execute_ethereum_indexer",
        image="ethereum-indexer-pipeline:latest",
        api_version="auto",
        auto_remove=True,
        command='sh -c "python src/extract.py && python src/transform.py"',
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
    )

    run_etl