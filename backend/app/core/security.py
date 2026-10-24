import base64
import hashlib

from cryptography.fernet import Fernet

from .config import get_settings


def _fernet_key() -> bytes:
    key = get_settings().fernet_key
    if key:
        return key.encode()
    # 本地开发默认密钥，仅用于单机开发；生产环境必须通过 FERNET_KEY 注入。
    return base64.urlsafe_b64encode(hashlib.sha256(b"datamind-local-dev-key").digest())


def encrypt_secret(plain: str) -> str:
    return Fernet(_fernet_key()).encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    return Fernet(_fernet_key()).decrypt(token.encode()).decode()

