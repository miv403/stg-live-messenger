import hashlib
import base64
from Crypto.Cipher import DES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes


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


def encrypt_des_cbc(des_key: bytes, plaintext: str) -> bytes:
    """Encrypt plaintext using DES-CBC with PKCS7 padding.
    
    Args:
        des_key: 8-byte DES key
        plaintext: Unicode string to encrypt
    
    Returns:
        bytes: iv (8 bytes) concatenated with ciphertext bytes
    """
    if not isinstance(des_key, (bytes, bytearray)) or len(des_key) != 8:
        raise ValueError("DES key must be 8 bytes")
    iv = get_random_bytes(8)
    cipher = DES.new(des_key, DES.MODE_CBC, iv)
    data = plaintext.encode('utf-8')
    ct = cipher.encrypt(pad(data, 8))
    return iv + ct


def decrypt_des_cbc(des_key: bytes, iv_ciphertext: bytes) -> str:
    """Decrypt iv|ciphertext using DES-CBC with PKCS7 unpadding.
    
    Args:
        des_key: 8-byte DES key
        iv_ciphertext: bytes where first 8 bytes are IV followed by ciphertext
    
    Returns:
        str: decrypted Unicode string
    """
    if not isinstance(des_key, (bytes, bytearray)) or len(des_key) != 8:
        raise ValueError("DES key must be 8 bytes")
    if not isinstance(iv_ciphertext, (bytes, bytearray)) or len(iv_ciphertext) < 16:
        raise ValueError("Invalid iv+ciphertext input")
    iv = iv_ciphertext[:8]
    ct = iv_ciphertext[8:]
    cipher = DES.new(des_key, DES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(ct), 8)
    return pt.decode('utf-8')


def encrypt_des_cbc_b64(des_key: bytes, plaintext: str) -> str:
    """Encrypt and return base64 string of iv|ciphertext."""
    return base64.b64encode(encrypt_des_cbc(des_key, plaintext)).decode('ascii')


def decrypt_des_cbc_b64(des_key: bytes, b64_iv_cipher: str) -> str:
    """Decrypt base64 iv|ciphertext and return plaintext string."""
    raw = base64.b64decode(b64_iv_cipher)
    return decrypt_des_cbc(des_key, raw)

