"""
Sample Codebase — A micro Python payment/order system with seeded bugs, features,
and achievements (technical debt). Every entity is documented so the entity graph
can be built deterministically.

Entities:
  FEATURE: payment_process, order_create, order_cancel, webhook_notify
  MODULE:  api, database, frontend, backend, auth, notification
  API:     /api/pay, /api/order, /api/webhook
  BUG:     token_expiry, race_condition, null_handler
  ACHIEVEMENT: missing_tests, no_logging, legacy_auth
"""

PAYMENT_PROCESS = {
    "name": "payment_process",
    "type": "FEATURE",
    "connects": ["api_pay", "db_transact", "auth_check", "frontend_pay_btn"],
    "sub_entities": ["payment_validation", "refund_handler"],
}

ORDER_CREATE = {
    "name": "order_create",
    "type": "FEATURE",
    "connects": ["api_order", "db_orders", "webhook_notify"],
    "sub_entities": ["inventory_check", "price_calc"],
}

ORDER_CANCEL = {
    "name": "order_cancel",
    "type": "FEATURE",
    "connects": ["api_cancel", "db_orders", "webhook_notify", "refund_handler"],
    "sub_entities": ["cancellation_policy", "refund_handler"],
}

WEBHOOK_NOTIFY = {
    "name": "webhook_notify",
    "type": "FEATURE",
    "connects": ["api_webhook", "notification_service", "frontend_status"],
    "sub_entities": ["retry_logic", "payload_parser"],
}


API_PAY = {
    "name": "/api/pay",
    "type": "API",
    "connects": ["payment_process", "auth_check"],
    "depends_on": ["auth_token"],
}

API_ORDER = {
    "name": "/api/order",
    "type": "API",
    "connects": ["order_create"],
    "depends_on": ["auth_token", "inventory_check"],
}

API_CANCEL = {
    "name": "/api/cancel",
    "type": "API",
    "connects": ["order_cancel"],
    "depends_on": ["auth_token"],
}

API_WEBHOOK = {
    "name": "/api/webhook",
    "type": "API",
    "connects": ["webhook_notify"],
    "depends_on": ["webhook_secret"],
}


DB_TRANSACT = {
    "name": "db_transact",
    "type": "MODULE",
    "connects": ["payment_process"],
    "depends_on": ["db_connection"],
}

DB_ORDERS = {
    "name": "db_orders",
    "type": "MODULE",
    "connects": ["order_create", "order_cancel"],
    "depends_on": ["db_connection"],
}


FRONTEND_PAY_BTN = {
    "name": "frontend_pay_btn",
    "type": "MODULE",
    "connects": ["payment_process"],
    "calls": ["/api/pay"],
}

FRONTEND_STATUS = {
    "name": "frontend_status",
    "type": "MODULE",
    "connects": ["webhook_notify"],
    "calls": ["/api/webhook"],
}


AUTH_CHECK = {
    "name": "auth_check",
    "type": "MODULE",
    "connects": ["/api/pay", "/api/order", "/api/cancel"],
    "depends_on": ["auth_token"],
}

AUTH_TOKEN = {
    "name": "auth_token",
    "type": "BUG",
    "connects": ["auth_check", "frontend_pay_btn"],
    "symptom": "API returns 401 after token expires mid-session",
    "root_cause": "Token not refreshed on /api/pay → /api/cancel cascade",
    "severity": 0.8,
}

RACE_CONDITION = {
    "name": "race_condition",
    "type": "BUG",
    "connects": ["order_create", "inventory_check"],
    "symptom": "Double-charging when order_create and refund_handler fire simultaneously",
    "root_cause": "No transaction lock around inventory_check",
    "severity": 0.9,
}

NULL_HANDLER = {
    "name": "null_handler",
    "type": "BUG",
    "connects": ["webhook_notify", "payload_parser"],
    "symptom": "NullPointerException when webhook payload has missing fields",
    "root_cause": "payload_parser doesn't guard against None fields",
    "severity": 0.6,
}


NOTIFICATION_SERVICE = {
    "name": "notification_service",
    "type": "MODULE",
    "connects": ["webhook_notify"],
}

RETRY_LOGIC = {
    "name": "retry_logic",
    "type": "MODULE",
    "connects": ["webhook_notify"],
}

REFUND_HANDLER = {
    "name": "refund_handler",
    "type": "MODULE",
    "connects": ["payment_process", "order_cancel", "order_create"],
}


MISSING_TESTS = {
    "name": "missing_tests",
    "type": "ACHIEVEMENT",
    "connects": ["payment_process", "webhook_notify"],
    "description": "Critical payment flows lack unit tests",
}

NO_LOGGING = {
    "name": "no_logging",
    "type": "ACHIEVEMENT",
    "connects": ["api_pay", "api_webhook"],
    "description": "No structured logging for audit trail",
}

LEGACY_AUTH = {
    "name": "legacy_auth",
    "type": "ACHIEVEMENT",
    "connects": ["auth_check"],
    "description": "Using SHA-1 for password hashing; should be Argon2",
}


ENTITY_INDEX = [
    PAYMENT_PROCESS, ORDER_CREATE, ORDER_CANCEL, WEBHOOK_NOTIFY,
    API_PAY, API_ORDER, API_CANCEL, API_WEBHOOK,
    DB_TRANSACT, DB_ORDERS,
    FRONTEND_PAY_BTN, FRONTEND_STATUS,
    AUTH_CHECK, AUTH_TOKEN, RACE_CONDITION, NULL_HANDLER,
    NOTIFICATION_SERVICE, RETRY_LOGIC, REFUND_HANDLER,
    MISSING_TESTS, NO_LOGGING, LEGACY_AUTH,
]


CHANGE_PROPOSALS = [
    {
        "id": "rename_payment_process",
        "description": "Rename function payment_process → process_payment",
        "affected": ["payment_process"],
        "expected_impact": ["api_pay", "db_transact", "refund_handler"],
        "introduces_bug": None,
    },
    {
        "id": "rename_api_pay",
        "description": "Rename endpoint /api/pay → /v2/pay",
        "affected": ["/api/pay"],
        "expected_impact": ["payment_process", "frontend_pay_btn"],
        "introduces_bug": None,
    },
    {
        "id": "rename_auth_token_bug",
        "description": "Rename auth_token → session_token",
        "affected": ["auth_token"],
        "expected_impact": ["auth_check", "frontend_pay_btn", "/api/pay", "/api/order", "/api/cancel"],
        "introduces_bug": "auth_token",  # cascades: token expiry triggers 401
    },
    {
        "id": "rename_race_condition_bug",
        "description": "Rename order_create → create_order",
        "affected": ["order_create"],
        "expected_impact": ["api_order", "refund_handler", "order_cancel"],
        "introduces_bug": "race_condition",
    },
    {
        "id": "rename_null_handler_bug",
        "description": "Rename webhook_notify → notify_webhook",
        "affected": ["webhook_notify"],
        "expected_impact": ["api_webhook", "frontend_status", "retry_logic"],
        "introduces_bug": "null_handler",
    },
    {
        "id": "rename_refund_handler",
        "description": "Rename refund_handler → handle_refund",
        "affected": ["refund_handler"],
        "expected_impact": ["payment_process", "order_cancel", "order_create"],
        "introduces_bug": None,
    },
    {
        "id": "rename_inventory_check",
        "description": "Rename inventory_check → check_inventory",
        "affected": ["inventory_check"],
        "expected_impact": ["order_create"],
        "introduces_bug": "race_condition",
    },
    {
        "id": "rename_frontend_pay_btn",
        "description": "Rename frontend_pay_btn → pay_button_component",
        "affected": ["frontend_pay_btn"],
        "expected_impact": ["payment_process", "/api/pay"],
        "introduces_bug": None,
    },
    {
        "id": "rename_webhook_secret",
        "description": "Rename webhook_secret → webhook_api_key",
        "affected": ["webhook_secret"],
        "expected_impact": ["api_webhook"],
        "introduces_bug": None,
    },
    {
        "id": "rename_db_transact",
        "description": "Rename db_transact → db_transaction",
        "affected": ["db_transact"],
        "expected_impact": ["payment_process"],
        "introduces_bug": None,
    },
]