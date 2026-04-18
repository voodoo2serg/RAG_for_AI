import logging
import os
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class SecretBroker:
    """Encrypts and decrypts secrets using Fernet symmetric encryption."""

    def __init__(self):
        key = getattr(settings, "SECRET_MASTER_KEY", "") or os.environ.get("SECRET_MASTER_KEY", "")
        allow_plaintext = bool(getattr(settings, "ALLOW_PLAINTEXT_SECRETS_IN_DEV", False))
        if not key:
            if allow_plaintext:
                logger.warning("SECRET_MASTER_KEY not set; DEV plaintext secret mode enabled.")
                self._fernet = None
            else:
                raise ImproperlyConfigured("SECRET_MASTER_KEY must be set unless ALLOW_PLAINTEXT_SECRETS_IN_DEV=true")
        else:
            if isinstance(key, str):
                key = key.encode()
            self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> bytes:
        if not self._fernet:
            return plaintext.encode()
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        if not self._fernet:
            return ciphertext.decode() if isinstance(ciphertext, bytes) else str(ciphertext)
        return self._fernet.decrypt(ciphertext).decode()

    def is_available(self) -> bool:
        return self._fernet is not None


def get_secret_broker() -> SecretBroker:
    return SecretBroker()


def generate_master_key() -> str:
    return Fernet.generate_key().decode()
