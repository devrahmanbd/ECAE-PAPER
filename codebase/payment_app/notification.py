"""Notification service — sends emails, SMS, push notifications."""

from typing import List, Dict, Optional
import time


class NotificationService:
    """Multi-channel notification dispatcher."""

    def __init__(self):
        self.channels: Dict[str, bool] = {
            "email": True,
            "sms": True,
            "push": True,
        }
        self._sent_queue: List[dict] = []
        self._template_cache: Dict[str, str] = {}

    def send_email(self, to: str, subject: str, body: str, template: Optional[str] = None) -> dict:
        """Send an email notification."""
        if not self.channels.get("email"):
            return {"status": "failed", "reason": "email_disabled"}
        if template:
            body = self._render_template(template, {"to": to, "subject": subject})
        self._sent_queue.append({
            "type": "email",
            "to": to,
            "subject": subject,
            "timestamp": time.time(),
        })
        return {"status": "sent", "message_id": f"email_{int(time.time())}"}

    def send_sms(self, phone: str, message: str) -> dict:
        """Send an SMS notification."""
        if not self.channels.get("sms"):
            return {"status": "failed", "reason": "sms_disabled"}
        self._sent_queue.append({
            "type": "sms",
            "phone": phone,
            "message": message,
            "timestamp": time.time(),
        })
        return {"status": "sent", "message_id": f"sms_{int(time.time())}"}

    def send_push(self, user_id: str, title: str, body: str, data: Optional[dict] = None) -> dict:
        """Send a push notification."""
        if not self.channels.get("push"):
            return {"status": "failed", "reason": "push_disabled"}
        self._sent_queue.append({
            "type": "push",
            "user_id": user_id,
            "title": title,
            "body": body,
            "data": data or {},
            "timestamp": time.time(),
        })
        return {"status": "sent", "message_id": f"push_{int(time.time())}"}

    def _render_template(self, template_name: str, context: dict) -> str:
        """Render a notification template."""
        if template_name in self._template_cache:
            template = self._template_cache[template_name]
        else:
            template = f"Notification: {context.get('subject', 'No subject')}"
        return template

    def get_sent_history(self, channel: Optional[str] = None, limit: int = 100) -> List[dict]:
        """Retrieve sent notification history."""
        if channel:
            filtered = [n for n in self._sent_queue if n["type"] == channel]
        else:
            filtered = self._sent_queue
        return filtered[-limit:]

    def enable_channel(self, channel: str) -> None:
        """Enable a notification channel."""
        if channel in self.channels:
            self.channels[channel] = True

    def disable_channel(self, channel: str) -> None:
        """Disable a notification channel."""
        if channel in self.channels:
            self.channels[channel] = False