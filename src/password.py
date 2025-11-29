import hashlib


def hash_password(password):
    """Compute SHA-256 hash of password.
    
    Args:
        password: Password string
        
    Returns:
        bytes: SHA-256 hash (32 bytes)
    """
    return hashlib.sha256(password.encode('utf-8')).digest()


def derive_des_key(username, password_hash):
    """Derive DES key from username (salt) and password hash using PBKDF2.
    
    Args:
        username: Username string (used as salt)
        password_hash: Password hash as bytes (32 bytes)
        
    Returns:
        bytes: DES key (8 bytes)
    """
    # Use PBKDF2 with password_hash as password, username as salt
    # dkLen=8 for DES key, count=10000 iterations
    des_key = hashlib.pbkdf2_hmac(
        'sha256',
        password_hash,
        username.encode('utf-8'),
        10000,
        dklen=8
    )
    return des_key


def get_password_hash_prefix(password_hash):
    """Get first 8 bytes of password hash for login verification.
    
    Args:
        password_hash: Password hash as bytes (32 bytes)
        
    Returns:
        bytes: First 8 bytes of hash
    """
    return password_hash[:8]


def derive_des_key_from_hash(username, password_hash):
    """Derive DES key from stored password hash and username.
    
    This is the same as derive_des_key but provided for clarity
    when working with stored hashes.
    
    Args:
        username: Username string (used as salt)
        password_hash: Password hash as bytes (32 bytes)
        
    Returns:
        bytes: DES key (8 bytes)
    """
    return derive_des_key(username, password_hash)

