"""Webhook handler — processes external payment gateway webhooks."""

from typing import Dict, Optional
import json
import hashlib
import time


class WebhookHandler:
    """Handles incoming webhook notifications from payment gateways."""

    def __init__(self, secret: str = ""):
        self.secret = secret
        self.events: list = []
        self._notification_service = None
        self._order_manager = None

    def handle_webhook(self, payload: bytes, signature: str) -> dict:
        """Process incoming webhook payload."""
        if not self._verify_signature(payload, signature):
            return {"status": "rejected", "reason": "invalid_signature"}

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return {"status": "rejected", "reason": "invalid_json"}

        event_type = data.get("type", "unknown")
        event_data = data.get("data", {})

        if event_type == "payment.succeeded":
            return self._handle_payment_success(event_data)
        elif event_type == "payment.failed":
            return self._handle_payment_failure(event_data)
        elif event_type == "refund.processed":
            return self._handle_refund(event_data)
        elif event_type == "subscription.updated":
            return self._handle_subscription_update(event_data)
        else:
            return self._handle_unknown_event(event_type, event_data)

    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature."""
        if not self.secret:
            return True
        expected = hashlib.sha256(self.secret.encode()).hexdigest()
        return signature == expected

    def _handle_payment_success(self, data: Dict) -> dict:
        """Handle successful payment webhook."""
        tx_id = data.get("tx_id")
        order_id = data.get("order_id")
        self.events.append({
            "type": "payment.succeeded",
            "tx_id": tx_id,
            "order_id": order_id,
            "timestamp": time.time(),
        })
        if self._order_manager:
            self._order_manager.update_order_status(order_id, "paid")
        self._send_admin_notification("payment_success", data)
        return {"status": "processed", "event": "payment.succeeded"}

    def _handle_payment_failure(self, data: Dict) -> dict:
        """Handle failed payment webhook."""
        tx_id = data.get("tx_id")
        order_id = data.get("order_id")
        reason = data.get("reason", "unknown")
        self.events.append({
            "type": "payment.failed",
            "tx_id": tx_id,
            "order_id": order_id,
            "reason": reason,
            "timestamp": time.time(),
        })
        if self._order_manager:
            self._order_manager.update_order_status(order_id, "payment_failed")
        self._send_admin_notification("payment_failed", data)
        return {"status": "processed", "event": "payment.failed"}

    def _handle_refund(self, data: Dict) -> dict:
        """Handle refund processed webhook."""
        self.events.append({
            "type": "refund.processed",
            "refund_id": data.get("refund_id"),
            "tx_id": data.get("tx_id"),
            "timestamp": time.time(),
        })
        return {"status": "processed", "event": "refund.processed"}

    def _handle_subscription_update(self, data: Dict) -> dict:
        """Handle subscription update webhook."""
        self.events.append({
            "type": "subscription.updated",
            "subscription_id": data.get("subscription_id"),
            "status": data.get("status"),
            "timestamp": time.time(),
        })
        return {"status": "processed", "event": "subscription.updated"}

    def _handle_unknown_event(self, event_type: str, data: Dict) -> dict:
        """Handle unknown event types."""
        self.events.append({
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
        })
        return {"status": "ignored", "event": event_type}

    def _send_admin_notification(self, event: str, data: Dict) -> None:
        """Send notification to admin."""
        pass

    def get_events(self, event_type: Optional[str] = None) -> list:
        """Retrieve stored webhook events."""
        if event_type:
            return [e for e in self.events if e["type"] == event_type]
        return self.events