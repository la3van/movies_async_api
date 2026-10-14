"""Encryption and normalized phone lookup without storing plaintext PII."""

import base64
import hashlib
import hmac
import json
from uuid import UUID

import phonenumbers
from cryptography.fernet import Fernet, InvalidToken, MultiFernet


def normalize_phone(value: str) -> str:
    value = value.strip()
    if not value.startswith("+"):
        raise ValueError("Use an international phone number starting with +")
    try:
        number = phonenumbers.parse(value, None)
    except phonenumbers.NumberParseException as exc:
        raise ValueError("Invalid phone number") from exc
    if number.extension or not phonenumbers.is_valid_number(number):
        raise ValueError("Invalid phone number")
    return phonenumbers.format_number(
        number, phonenumbers.PhoneNumberFormat.E164
    )


class ProfileCipher:
    def __init__(self, keys: str, phone_key: str) -> None:
        self._fernet = MultiFernet(
            [Fernet(key.strip().encode()) for key in keys.split(",")]
        )
        self._phone_key = base64.urlsafe_b64decode(phone_key)

    def encrypt(self, user_id: UUID, data: dict[str, str | None]) -> str:
        payload = {"user_id": str(user_id), "data": data}
        return self._fernet.encrypt(
            json.dumps(payload, ensure_ascii=False).encode()
        ).decode()

    def decrypt(self, user_id: UUID, token: str) -> dict[str, str | None]:
        try:
            payload = json.loads(self._fernet.decrypt(token.encode()))
            data = payload["data"]
            if payload["user_id"] != str(user_id) or not isinstance(
                data, dict
            ):
                raise ValueError
            if not all(
                isinstance(k, str) and (v is None or isinstance(v, str))
                for k, v in data.items()
            ):
                raise ValueError
            return data
        except (InvalidToken, ValueError, KeyError, TypeError) as exc:
            raise ValueError("profile_decryption_failed") from exc

    def phone_index(self, phone: str | None) -> str | None:
        if phone is None:
            return None
        return hmac.new(
            self._phone_key, phone.encode(), hashlib.sha256
        ).hexdigest()

    def rotate(self, token: str) -> str:
        return self._fernet.rotate(token.encode()).decode()
