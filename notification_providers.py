import os
import logging
import requests
from abc import ABC, abstractmethod
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

class NotificationProvider(ABC):
    @abstractmethod
    def send_notification(self, title: str, message: str) -> bool:
        pass

class GotifyProvider(NotificationProvider):
    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.token = token

    def send_notification(self, title: str, message: str) -> bool:
        try:
            response = requests.post(
                f"{self.url}/message",
                json={
                    "title": title,
                    "message": message,
                    "priority": 5
                },
                headers={"X-Gotify-Key": self.token}
            )
            response.raise_for_status()
            logger.info("Notification sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

class SlackProvider(NotificationProvider):
    def __init__(self, token: str, channel: str = '#monitoring'):
        self.token = token
        self.channel = channel

    def send_notification(self, title: str, message: str) -> bool:
        try:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            # Format message for Slack
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message.replace('\n', '\n>')
                    }
                }
            ]
            
            response = requests.post(
                'https://slack.com/api/chat.postMessage',
                headers=headers,
                json={
                    'channel': self.channel,
                    'blocks': blocks
                }
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            if not response_data.get('ok', False):
                raise Exception(f"Slack API error: {response_data.get('error', 'Unknown error')}")
            
            logger.info("Slack notification sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

def get_notification_provider(config: dict) -> NotificationProvider:
    """Factory function to create the appropriate notification provider"""
    provider_type = config.get('notifications', {}).get('provider', 'gotify').lower()
    
    if provider_type == 'gotify':
        gotify_url = config.get('notifications', {}).get('gotify', {}).get('url')
        token = os.getenv('GOTIFY_TOKEN')
        if not gotify_url or not token:
            raise ValueError("Gotify URL and token are required for Gotify notifications")
        return GotifyProvider(gotify_url, token)
    
    elif provider_type == 'slack':
        token = os.getenv('SLACK_TOKEN')
        channel = config.get('notifications', {}).get('slack', {}).get('channel', '#monitoring')
        if not token:
            raise ValueError("Slack token is required for Slack notifications")
        return SlackProvider(token, channel)
    
    else:
        raise ValueError(f"Unsupported notification provider: {provider_type}")

