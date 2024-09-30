"""
This file contains common cryptographic-related utilities for use by both the Client
and Server implementations of the OLAF-Neighborhood protocol.

Functions include key generation, encryption, decryption, and handling of public/private keys.
"""

import base64
import json
import os
import hashlib
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Generate private key for client
def generate_private_key():
    """Generate a new RSA private key.

    Returns:
        A private key object.
    """
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

def get_public_key(private_key):
    """Return a base64-encoded PEM public key from the given private key.

    Args:
        private_key: The RSA private key object.

    Returns:
        A base64-encoded string of the public key in PEM format.
    """
    public_key = private_key.public_key()
    pem_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return base64.b64encode(pem_public_key).decode('utf-8')

def get_fingerprint(public_key):
    """Generate a base64-encoded fingerprint from a public key.

    Args:
        public_key: A string representation of the public key.

    Returns:
        A base64-encoded fingerprint of the public key.
    """
    sha256_hash = hashlib.sha256()
    sha256_hash.update(public_key.encode('utf-8'))
    binary_fingerprint = sha256_hash.digest()
    base64_fingerprint = base64.b64encode(binary_fingerprint).decode('utf-8')
    return base64_fingerprint

def base64_to_pem(pem_string):
    """Convert a base64-encoded PEM string back to a public key object.

    Args:
        pem_string: A base64-encoded string of the PEM public key.

    Returns:
        A public key object.
    """
    return serialization.load_pem_public_key(
        base64.b64decode(pem_string.encode('utf-8')),
        backend=default_backend()
    )

def pem_to_base64(pem_key):
    """Convert a PEM public key object to a base64-encoded string.

    Args:
        pem_key: The public key object in PEM format.

    Returns:
        A base64-encoded string of the public key.
    """
    return base64.b64encode(pem_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )).decode('utf-8')

def decrypt_symm_key(encoded_encrypted_symm_key, private_key):
    """Decrypt a base64-encoded encrypted symmetric key using the provided private key.

    Args:
        encoded_encrypted_symm_key: The base64-encoded encrypted symmetric key.
        private_key: The private key used for decryption.

    Returns:
        The decrypted symmetric key.
    """
    encrypted_symm_key = base64.b64decode(encoded_encrypted_symm_key)
    symm_key = private_key.decrypt(
        encrypted_symm_key,
        rsa_padding.OAEP(
            mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return symm_key

def decrypt_message(decrypted_symm_key, message, iv):
    """Decrypt a message using the provided symmetric key and IV.

    Args:
        decrypted_symm_key: The symmetric key used for decryption.
        message: The base64-encoded encrypted message (which includes the authentication tag).
        iv: The base64-encoded initialization vector used during encryption.

    Returns:
        The decrypted message as a JSON object, or None if decryption fails.
    """
    # Decode the base64-encoded message and IV from utf-8 strings
    message = base64.b64decode(message.encode('utf-8'))  # Convert to bytes first, then decode from base64

    # Initialize AES GCM for decryption
    aesgcm = AESGCM(decrypted_symm_key)

    try:
        # Decrypt the message. AESGCM automatically handles authentication tag verification.
        decrypted_data = aesgcm.decrypt(iv, message, None)

        # Convert decrypted bytes to JSON object
        data = json.loads(decrypted_data.decode('utf-8'))
    except (json.JSONDecodeError, InvalidTag):
        # Return None if decryption fails due to invalid tag or JSON parsing issues
        return None
    
    return data

def encrypt_message(key, message):
    """Encrypt a message using the provided symmetric key.

    Args:
        key: The symmetric key used for encryption.
        message: The message to encrypt as a JSON object.

    Returns:
        A dictionary containing the encrypted message and the initialization vector (IV).
    """
    message_bytes = json.dumps(message).encode('utf-8')
    iv = os.urandom(16)  # Generate random initialization vector
    aesgcm = AESGCM(key)
    encrypted_message = aesgcm.encrypt(iv, message_bytes, None)

    encryption_data = {
        'message': base64.b64encode(encrypted_message).decode('utf-8'),
        'iv': base64.b64encode(iv).decode('utf-8')
    }

    return encryption_data

def generate_key():
    """Generate a random 32-byte symmetric key.

    Returns:
        A 16-byte symmetric key.
    """
    return os.urandom(16)

def encrypt_symm_keys(symm_key, *recipients):
    """Encrypt a symmetric key for multiple recipients using their public keys.

    Args:
        symm_key: The symmetric key to encrypt (should be in bytes).
        recipients: Base64-encoded UTF-8 strings of public keys.

    Returns:
        A list of base64-encoded encrypted symmetric keys.
    """
    encrypted_symm_keys = []
    for recipient in recipients:
        # Decode the base64-encoded public key
        decoded_key = base64.b64decode(recipient.encode('utf-8'))
        public_key = serialization.load_pem_public_key(
            decoded_key,
            backend=default_backend()
        )
        ciphertext = public_key.encrypt(
            symm_key,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        encrypted_symm_keys.append(base64.b64encode(ciphertext).decode('utf-8'))
    return encrypted_symm_keys

def sign_data(private_key, data):
    return private_key.sign(
        data,
        rsa_padding.PSS(
            mgf=rsa_padding.MGF1(hashes.SHA256()),
            salt_length=rsa_padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )