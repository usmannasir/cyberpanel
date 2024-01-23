import uuid
import bcrypt
import hashlib

def hash_password(password):
    # uuid is used to generate a random number
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt


def check_password(hashed_password, user_password):
    password, salt = hashed_password.split(':')
    return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()

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
