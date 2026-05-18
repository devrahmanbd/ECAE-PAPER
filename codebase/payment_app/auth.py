"""Authentication module — token management and session handling."""

from typing import Optional, Dict
import hashlib
import time
import secrets


class AuthManager:
    """Manages authentication, tokens, and user sessions."""

    def __init__(self):
        self.tokens: Dict[str, dict] = {}
        self.users: Dict[str, dict] = {}
        self._sessions: Dict[str, str] = {}

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user and issue token."""
        if username not in self.users:
            return None
        user = self.users[username]
        if not self._verify_password(password, user["password_hash"]):
            return None
        token = self._generate_token(username)
        self.tokens[token] = {
            "username": username,
            "created_at": time.time(),
            "expires_at": time.time() + 3600,
        }
        self._sessions[username] = token
        return {"token": token, "expires_at": time.time() + 3600}

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against stored hash."""
        h = hashlib.sha256(password.encode()).hexdigest()
        return h == password_hash

    def _generate_token(self, username: str) -> str:
        """Generate a new auth token."""
        return secrets.token_urlsafe(32)

    def validate_token(self, token: str) -> bool:
        """Validate an auth token."""
        if token not in self.tokens:
            return False
        token_data = self.tokens[token]
        if time.time() > token_data["expires_at"]:
            del self.tokens[token]
            return False
        return True

    def refresh_token(self, token: str) -> Optional[dict]:
        """Refresh an auth token."""
        if not self.validate_token(token):
            return None
        old_data = self.tokens[token]
        username = old_data["username"]
        del self.tokens[token]
        new_token = self._generate_token(username)
        self.tokens[new_token] = {
            "username": username,
            "created_at": time.time(),
            "expires_at": time.time() + 3600,
        }
        return {"token": new_token, "expires_at": time.time() + 3600}

    def revoke_token(self, token: str) -> bool:
        """Revoke an auth token."""
        if token in self.tokens:
            del self.tokens[token]
            return True
        return False

    def get_token_info(self, token: str) -> Optional[dict]:
        """Get information about a token."""
        return self.tokens.get(token)

    def register_user(self, username: str, password: str, email: str) -> dict:
        """Register a new user."""
        if username in self.users:
            return {"status": "failed", "reason": "username_taken"}
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.users[username] = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "created_at": time.time(),
        }
        return {"status": "success", "username": username}