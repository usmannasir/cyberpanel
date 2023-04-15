import sys
from crypt import crypt, METHOD_SHA512
from getpass import getpass

print(crypt('hosting', METHOD_SHA512))