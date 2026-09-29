from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models

PREFIX = "enc:v1:"


def _fernet():
    key = settings.FERNET_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_value(value):
    if value is None or value == "":
        return value
    if isinstance(value, str) and value.startswith(PREFIX):
        return value
    token = _fernet().encrypt(value.encode()).decode()
    return PREFIX + token


def decrypt_value(value):
    if value is None or value == "":
        return value
    if not str(value).startswith(PREFIX):
        return value
    token = str(value)[len(PREFIX) :]
    return _fernet().decrypt(token.encode()).decode()


class EncryptedTextField(models.TextField):
    """Fernet-encrypted text. Empty values stay empty so forms can leave secrets unchanged."""

    def from_db_value(self, value, expression, connection):
        return decrypt_value(value)

    def to_python(self, value):
        return decrypt_value(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt_value(value)
