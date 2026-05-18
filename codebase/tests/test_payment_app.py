# Payment App Test Suite


def test_payment_processor():
    from payment_app.payment import PaymentProcessor
    pp = PaymentProcessor()
    result = pp.process_payment("order_123", 100.0, "valid_token_abc")
    assert result["status"] == "success"
    assert "tx_id" in result


def test_order_manager():
    from payment_app.order import OrderManager
    om = OrderManager()
    result = om.create_order("user_1", [{"product_id": "p1", "quantity": 2}], "123 Main St")
    assert result["status"] == "success"
    assert "order_id" in result


def test_webhook_handler():
    from payment_app.webhook import WebhookHandler
    import json
    wh = WebhookHandler(secret="")
    payload = json.dumps({"type": "payment.succeeded", "data": {"tx_id": "tx1", "order_id": "o1"}}).encode()
    result = wh.handle_webhook(payload, "")
    assert result["status"] == "processed"


def test_auth_manager():
    from payment_app.auth import AuthManager
    am = AuthManager()
    am.register_user("testuser", "password123", "test@example.com")
    result = am.authenticate("testuser", "password123")
    assert result is not None
    assert "token" in result


def test_notification_service():
    from payment_app.notification import NotificationService
    ns = NotificationService()
    result = ns.send_email("test@example.com", "Subject", "Body")
    assert result["status"] == "sent"


def test_database():
    from payment_app.database import Database
    db = Database()
    db.insert_transaction("tx_test", "order_test", 50.0, "completed")
    tx = db.get_transaction("tx_test")
    assert tx is not None
    assert tx["tx_id"] == "tx_test"
    db.close()


def test_order_cancel():
    from payment_app.order import OrderManager
    om = OrderManager()
    create_result = om.create_order("user_1", [{"product_id": "p1", "quantity": 1}], "addr")
    order_id = create_result.get("order_id")
    cancel_result = om.cancel_order(order_id, "Changed my mind")
    assert cancel_result["status"] == "success"


def test_payment_refund():
    from payment_app.payment import PaymentProcessor
    pp = PaymentProcessor()
    pp.process_payment("order_1", 100.0, "tok")
    tx_id = list(pp.transactions.keys())[0]
    refund_result = pp.refund(tx_id, 50.0)
    assert refund_result["status"] == "success"


def test_invalid_token():
    from payment_app.payment import PaymentProcessor
    pp = PaymentProcessor()
    result = pp.process_payment("order_1", 100.0, "bad")
    assert result["status"] == "failed"
    assert result["reason"] == "invalid_token"


def test_order_not_found():
    from payment_app.order import OrderManager
    om = OrderManager()
    result = om.get_order("nonexistent_order")
    assert result is None


if __name__ == "__main__":
    import sys
    failed = []
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS: {name}")
            except Exception as e:
                print(f"FAIL: {name} — {e}")
                failed.append(name)
    if failed:
        print(f"\n{len(failed)} test(s) failed")
        sys.exit(1)
    else:
        print("\nAll tests passed")