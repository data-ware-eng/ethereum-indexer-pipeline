# 🌐 Ethereum Identity & Access Indexer Pipeline

A robust, modular Python ETL pipeline designed to fetch, clean, and secure network access logs and Web3 identity data.

- **Extract**: Fetches data from the DummyJSON API with fallback encoding management.
- **Transform & Security Screening**:
  - Normalizes text, spaces, and columns.
  - Converts data types to Int64.
  - Detects malicious SQL injection patterns (e.g., DROP, SELECT) using regex.
- **Quarantine Isolation**: Automatically separates suspicious records into a quarantine folder.
- **Observability**: Complete local logging in pipeline.log and real-time alerts via Slack Webhooks.

## 📂 Project Structure

- dags/ -> Airflow DAG orchestrating the automated workflow
- src/ -> Python scripts (extract, transform, notifications)
- sql/ -> Database schemas
- data/ -> Local clean data storage
- quarantine/ -> Isolated suspicious records
- Dockerfile -> Application container configuration
- .env -> Safe environment credentials
- .gitignore -> Protection rules to avoid leaks

## 🛠️ Tech Stack

- Python 3.11 (Pandas, SQLAlchemy, Requests)
- PostgreSQL
- Docker (Completed)

## 🗺️ Upcoming Features (Roadmap)

* **Power BI Dashboard:** Connect to PostgreSQL for advanced identity analytics and metrics.