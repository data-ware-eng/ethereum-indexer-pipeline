import os
import requests
import logging
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Configure logging to display timestamps and message levels
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Read the URL securely from the environment
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack_alert(message: str) -> None:
    """
    Dispatches an automated pipeline notification or alert directly to the Slack channel.
    Args:
        message (str): The payload text or alert log to be transmitted.
    """
    payload = {"text": message}

    try:
        logging.info("Initiating outbound API request to Slack...")
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)

        if response.status_code == 200 and response.text == "ok":
            logging.info("Notification successfully dispatched and confirmed by Slack!")
        else:
            logging.error(f"Slack API rejected transmission with HTTP {response.status_code}: {response.text}")

    except requests.exceptions.Timeout:
        logging.error("Connection attempt aborted: The request to Slack API timed out.")
    except requests.exceptions.RequestException as error:
        logging.error(f"Network transport layer failure encountered while contacting Slack: {error}")
    except Exception as general_error:
        logging.error(f"An unexpected technical anomaly occurred during notification lifecycle: {general_error}")

# --- SECURITY INTEGRATION VALIDATION ---
send_slack_alert("⚠️ CRITICAL SECURITY ALERT: ETL Pipeline detected a malicious threat. Infected file has been successfully isolated and quarantined. Immediate inspection required.")
