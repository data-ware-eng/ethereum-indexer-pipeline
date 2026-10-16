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

Programming Language: Python 3.11
Data Processing: Pandas
Database: PostgreSQL, SQLAlchemy
API Integration: Requests
Containerization: Docker
Workflow Orchestration: Apache Airflow
Monitoring & Alerts: Slack Webhooks
Business Intelligence: Power BI
Security Validation: Regex-Based Pattern Detectio

## 📊 Power BI Dashboard

The project includes a comprehensive security and analytics dashboard ('Yummy_Hacker_Injection.pbix') that details:
* **Account Distribution:** Clear breakdown of legitimate users, administrators, and moderators versus malicious injections.
* ** Incident Audit:** Identification and tracking of duplicate customer records utilized during the hacker attack vectors.

## 🐳 Docker Integration

Docker was integrated to containerize the entire ETL environment, providing a consistent and reproducible runtime across different systems. It simplifies deployment, dependency management, and environment configuration while ensuring reliable execution of all pipeline components.


## ⚙️ Apache Airflow Integration

Apache Airflow was integrated as the orchestration layer of the project, automating workflow scheduling, task dependency management, execution tracking, and operational monitoring. This ensures a reliable, scalable, and fully automated ETL process within a Dockerized environment.


## 📢 Slack Integration

Slack Webhooks were integrated to enhance observability and operational awareness across the pipeline. Real-time notifications are automatically delivered when workflow executions complete successfully or when errors occur, enabling faster monitoring and incident respons