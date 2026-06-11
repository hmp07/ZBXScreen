"""
加密解密工具
- AES-128-CBC 加密/解密（随机 IV，用于 Zabbix 密码存储）
- bcrypt 密码哈希（用于用户密码）
"""
import os
import base64
import hashlib
import bcrypt
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from config import settings


def _derive_key() -> bytes:
    """从 APP_SECRET_KEY 派生 16 字节 AES-128 密钥"""
    return hashlib.sha256(settings.app_secret_key.encode()).digest()[:16]


def encrypt_password(plaintext: str) -> str:
    """AES-128-CBC 加密，每次生成随机 IV，返回 base64(iv + ciphertext)"""
    key = _derive_key()
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
    return base64.b64encode(iv + ciphertext).decode()


def decrypt_password(encoded: str) -> str:
    """解密，从前 16 字节提取 IV"""
    raw = base64.b64decode(encoded)
    iv, ciphertext = raw[:16], raw[16:]
    cipher = AES.new(_derive_key(), AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), AES.block_size).decode()


def hash_password(password: str) -> str:
    """bcrypt 哈希用户密码"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """验证用户密码"""
    return bcrypt.checkpw(password.encode(), password_hash.encode())
