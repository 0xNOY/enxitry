import requests
import json

from .config import CONFIG


def send_message(message: str):
    """
    Slackにメッセージを送信する

    Args:
        message (str): メッセージ
    """
    requests.post(
        CONFIG.slack_webhook_url,
        data=json.dumps({"text": message}),
    )
