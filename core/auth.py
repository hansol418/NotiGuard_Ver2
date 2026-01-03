# STREAMLIT/core/auth.py
from __future__ import annotations

import base64
import hashlib
import hmac
import os


# -------------------------------------------------------
# 비밀번호 해시(데모용)
# - 실제 운영이면 bcrypt/argon2 권장
# - 여기서는 표준라이브러리로 PBKDF2 사용
# -------------------------------------------------------
_ITERATIONS = 120_000


def hash_password(password: str) -> str:
    """
    저장용 해시 문자열 생성
    format: pbkdf2$iters$salt_b64$dk_b64
    """
    password = (password or "").encode("utf-8")
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password, salt, _ITERATIONS, dklen=32)

    salt_b64 = base64.b64encode(salt).decode("ascii")
    dk_b64 = base64.b64encode(dk).decode("ascii")
    return f"pbkdf2${_ITERATIONS}${salt_b64}${dk_b64}"


def verify_password(password: str, stored: str) -> bool:
    """
    입력 비밀번호와 저장된 해시 비교
    """
    try:
        algo, iters_s, salt_b64, dk_b64 = stored.split("$", 3)
        if algo != "pbkdf2":
            return False

        iters = int(iters_s)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        dk_expected = base64.b64decode(dk_b64.encode("ascii"))

        dk = hashlib.pbkdf2_hmac(
            "sha256",
            (password or "").encode("utf-8"),
            salt,
            iters,
            dklen=len(dk_expected),
        )
        return hmac.compare_digest(dk, dk_expected)
    except Exception:
        return False
