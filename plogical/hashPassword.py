import uuid
import bcrypt
import hashlib

def hash_password(password):
    # Use bcrypt (slow, salted KDF) for new password hashes. Legacy salted
    # SHA-256 hashes ("<sha256hex>:<salt>") remain verifiable by check_password,
    # so existing accounts are not locked out and upgrade on next password set.
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(hashed_password, user_password):
    try:
        if hashed_password.startswith('$2'):
            return bcrypt.checkpw(user_password.encode(), hashed_password.encode())
        # Legacy format: "<sha256hex>:<salt>"
        password, salt = hashed_password.split(':')
        return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()
    except Exception:
        return False

# def generateToken(serverUserName, serverPassword):
#     credentials = '{0}:{1}'.format(serverUserName, serverPassword).encode()
#     encoded_credentials = base64.b64encode(credentials).decode()
#     return 'Basic {0}'.format(encoded_credentials)

# def hash_password(password):
#     salt = bcrypt.gensalt()
#     hashed_password = bcrypt.hashpw(password.encode(), salt)
#     return hashed_password.decode()
#
# def check_password(hashed_password, user_password):
#     return bcrypt.checkpw(user_password.encode(), hashed_password.encode())


def generateToken(username, password):
    # Concatenate username and password
    credentials = f'{username}:{password}'.encode()

    # Use SHA-256 hashing
    hashed_credentials = hashlib.sha256(credentials).hexdigest()

    return 'Basic {0}'.format(hashed_credentials)

def needs_password_rehash(hashed_password):
    """True when stored hash should be upgraded (legacy SHA-256:salt, or weak bcrypt cost)."""
    try:
        if not hashed_password:
            return True
        if not str(hashed_password).startswith('$2'):
            return True
        # bcrypt: $2b$12$... — rehash if cost factor below 12
        parts = str(hashed_password).split('$')
        if len(parts) >= 3 and parts[2].isdigit() and int(parts[2]) < 12:
            return True
        return False
    except Exception:
        return False
