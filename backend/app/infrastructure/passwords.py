from pwdlib import PasswordHash


def hash_password(password: str) -> str:
    hasher = PasswordHash.recommended()
    return hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    hasher = PasswordHash.recommended()
    return hasher.verify(password, password_hash)
