"""API routes — Flask-based REST API for the payment system."""

from flask import Flask, request, jsonify
from payment_app.payment import PaymentProcessor
from payment_app.order import OrderManager
from payment_app.webhook import WebhookHandler
from payment_app.auth import AuthManager
from payment_app.notification import NotificationService

app = Flask(__name__)

payment_processor = PaymentProcessor()
order_manager = OrderManager()
webhook_handler = WebhookHandler(secret="webhook_secret_key")
auth_manager = AuthManager()
notification_service = NotificationService()


@app.route("/api/pay", methods=["POST"])
def api_pay():
    """Process a payment."""
    data = request.get_json()
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not auth_manager.validate_token(token):
        return jsonify({"status": "error", "reason": "unauthorized"}), 401

    order_id = data.get("order_id")
    amount = data.get("amount")
    payment_token = data.get("payment_token")

    result = payment_processor.process_payment(order_id, amount, payment_token)
    status_code = 200 if result["status"] == "success" else 400
    return jsonify(result), status_code


@app.route("/api/order", methods=["POST"])
def api_order():
    """Create a new order."""
    data = request.get_json()
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not auth_manager.validate_token(token):
        return jsonify({"status": "error", "reason": "unauthorized"}), 401

    user_id = data.get("user_id")
    items = data.get("items", [])
    shipping_address = data.get("shipping_address")

    result = order_manager.create_order(user_id, items, shipping_address)
    status_code = 201 if result["status"] == "success" else 400
    return jsonify(result), status_code


@app.route("/api/cancel", methods=["POST"])
def api_cancel():
    """Cancel an order."""
    data = request.get_json()
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not auth_manager.validate_token(token):
        return jsonify({"status": "error", "reason": "unauthorized"}), 401

    order_id = data.get("order_id")
    reason = data.get("reason", "")
    result = order_manager.cancel_order(order_id, reason)
    status_code = 200 if result["status"] == "success" else 400
    return jsonify(result), status_code


@app.route("/api/webhook", methods=["POST"])
def api_webhook():
    """Receive webhook from payment gateway."""
    payload = request.get_data()
    signature = request.headers.get("X-Webhook-Signature", "")
    result = webhook_handler.handle_webhook(payload, signature)
    status_code = 200 if result["status"] in ("processed", "ignored") else 400
    return jsonify(result), status_code


@app.route("/api/refund", methods=["POST"])
def api_refund():
    """Process a refund."""
    data = request.get_json()
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not auth_manager.validate_token(token):
        return jsonify({"status": "error", "reason": "unauthorized"}), 401

    tx_id = data.get("tx_id")
    amount = data.get("amount")
    result = payment_processor.refund(tx_id, amount)
    status_code = 200 if result["status"] == "success" else 400
    return jsonify(result), status_code


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    """User login endpoint."""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    result = auth_manager.authenticate(username, password)
    if result:
        return jsonify(result), 200
    return jsonify({"status": "error", "reason": "invalid_credentials"}), 401


if __name__ == "__main__":
    app.run(debug=True, port=5000)