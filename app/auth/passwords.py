from passlib.context import CryptContext

# bcrypt has a fixed, deliberately slow cost factor and no known practical
# break — appropriate for password storage where the threat is offline
# brute force against a leaked hash, not throughput.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)
