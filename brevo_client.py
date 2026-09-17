import os
import requests
from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_NAME = os.getenv("SENDER_NAME", "NDMU Notification Console")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def send_brevo_email(recipient: str, message: str, subject: str = "NDMU Notification") -> str:
    """Send a real email through Brevo. Returns a delivery line."""
    if not BREVO_API_KEY or not SENDER_EMAIL:
        raise RuntimeError(
            "Missing BREVO_API_KEY or SENDER_EMAIL. Check your .env file."
        )

    stripped = message.strip()
    html_content = stripped if stripped.startswith("<") else f"<p>{message}</p>"

    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": recipient}],
        "subject": subject,
        "htmlContent": html_content,
    }
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    response = requests.post(BREVO_URL, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    message_id = response.json().get("messageId", "unknown-id")
    return f"BREVO EMAIL -> sent to {recipient} (<{message_id}>)"
