import random
import string

def generate_file_id():
    """Generate a unique file ID"""
    # pool of uppercase letters + digits
    pool = string.ascii_uppercase + string.digits
    # pick 7 random chars and prepend 'F' to make total length 8
    return 'F' + ''.join(random.choice(pool) for _ in range(7))