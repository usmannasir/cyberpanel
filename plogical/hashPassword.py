import uuid
import bcrypt
import hashlib

def hash_password(password):
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return '$bcrypt$' + hashed.decode('utf-8')


def check_password(hashed_password, user_password):
    if not hashed_password:
        return False
    if str(hashed_password).startswith('$bcrypt$'):
        stored = str(hashed_password)[8:].encode('utf-8')
        try:
            return bcrypt.checkpw(user_password.encode('utf-8'), stored)
        except ValueError:
            return False
    try:
        password, salt = hashed_password.split(':', 1)
    except ValueError:
        return False
    return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()


def needs_password_rehash(hashed_password):
    return not str(hashed_password or '').startswith('$bcrypt$')

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
