import secrets
import string

alphabet = string.ascii_letters + string.digits
the_password = ''.join(secrets.choice(alphabet) for _ in range(14))
print(the_password)