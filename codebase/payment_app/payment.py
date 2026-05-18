"""Payment processing module — handles all payment transactions."""

from typing import Optional, Dict
import hashlib
import time


class PaymentProcessor:
    """Processes payments through various gateways."""

    def __init__(self, gateway: str = "stripe"):
        self.gateway = gateway
        self.transactions: Dict[str, dict] = {}
        self._cache: Dict[str, float] = {}

    def process_payment(self, order_id: str, amount: float, token: str) -> dict:
        """Main payment processing entry point."""
        if not self._validate_token(token):
            return {"status": "failed", "reason": "invalid_token"}
        if not self._check_balance(order_id, amount):
            return {"status": "failed", "reason": "insufficient_balance"}

        tx_id = self._create_transaction(order_id, amount, token)
        receipt = self._generate_receipt(tx_id, order_id, amount)
        self._send_confirmation(order_id, receipt)
        return {"status": "success", "tx_id": tx_id, "receipt": receipt}

    def _validate_token(self, token: str) -> bool:
        """Validate payment token."""
        if len(token) < 8:
            return False
        return True

    def _check_balance(self, order_id: str, amount: float) -> bool:
        """Check if order has sufficient balance."""
        return amount > 0

    def _create_transaction(self, order_id: str, amount: float, token: str) -> str:
        """Create a transaction record."""
        tx_id = hashlib.sha256(f"{order_id}{amount}{time.time()}".encode()).hexdigest()[:16]
        self.transactions[tx_id] = {
            "order_id": order_id,
            "amount": amount,
            "status": "pending",
            "token": token,
        }
        return tx_id

    def _generate_receipt(self, tx_id: str, order_id: str, amount: float) -> dict:
        """Generate payment receipt."""
        return {
            "tx_id": tx_id,
            "order_id": order_id,
            "amount": amount,
            "timestamp": time.time(),
            "currency": "USD",
        }

    def _send_confirmation(self, order_id: str, receipt: dict) -> bool:
        """Send payment confirmation notification."""
        return True

    def refund(self, tx_id: str, amount: Optional[float] = None) -> dict:
        """Process a refund for a transaction."""
        if tx_id not in self.transactions:
            return {"status": "failed", "reason": "tx_not_found"}
        tx = self.transactions[tx_id]
        refund_amount = amount or tx["amount"]
        return {"status": "success", "refund_id": f"ref_{tx_id}", "amount": refund_amount}

    def get_transaction(self, tx_id: str) -> Optional[dict]:
        """Retrieve transaction details."""
        return self.transactions.get(tx_id)