import string
import random

def generate_pass(length=14):
  chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
  size = length
  return ''.join(random.choice(chars) for x in range(size))