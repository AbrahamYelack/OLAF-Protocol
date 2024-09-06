
import base64
import json
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

# Generate private key for client
def generate_private_key():
    return rsa.generate_private_key(
        public_exponent = 65537,
        key_size = 2048,
        backend=default_backend()
    )

# Function to return a string encoded exported PEM public key
def get_public_key(private_key):
    public_key = private_key.public_key()
    pem_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return base64.b64encode(pem_public_key).decode('utf-8')

def base64_to_pem(pem_string):
    return serialization.load_pem_public_key(
        base64.b64decode(pem_string.encode('utf-8')),
        backend = default_backend()
    )

# pem_to_base64_key utility function
def pem_to_base64(pem_key):
    return base64.b64encode(pem_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )).decode('utf-8')

def decrypt_symm_key(encoded_encrypted_symm_key, private_key):
    encrypted_symm_key = base64.b64decode(encoded_encrypted_symm_key)
    symm_key = private_key.decode(encrypted_symm_key)
    return symm_key

def decrypt_message(decrypted_symm_key, message, iv):
    message = base64.b64decode(message)
    iv = base64.b64decode(iv)
    aes_key = decrypted_symm_key
    encrypted_data = message
    mode = modes.GCM(iv)
    cipher = Cipher(algorithms.AES(aes_key), mode)
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
    try:
        data = json.loads(decrypted_data.decode('utf-8'))
    except:
        return None
    print(f"Decoded data: {decrypted_data}")
    return data
