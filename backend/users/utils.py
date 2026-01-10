import hashlib
import time
from datetime import datetime
from eth_account.messages import encode_defunct
from web3 import Web3
from django.conf import settings

def generate_siwe_message(wallet_address, chain_id, domain, uri, nonce=None):
    """
    Generate Sign-In with Ethereum (EIP-4361) message
    """
    if nonce is None:
        nonce = hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]
    
    current_time = datetime.utcnow().isoformat()
    
    message = f"{domain} wants you to sign in with your Ethereum account:\n{wallet_address}\n\n"
    message += f"URI: {uri}\n"
    message += f"Version: 1\n"
    message += f"Chain ID: {chain_id}\n"
    message += f"Nonce: {nonce}\n"
    message += f"Issued At: {current_time}"
    
    return message

def validate_siwe_signature(message, signature, expected_address):
    """
    Validate SIWE signature
    """
    try:
        web3 = Web3()
        message_hash = encode_defunct(text=message)
        recovered_address = web3.eth.account.recover_message(message_hash, signature=signature)
        
        return recovered_address.lower() == expected_address.lower(), recovered_address.lower()
    except Exception as e:
        print(f"Signature validation error: {e}")
        return False, None

def validate_eth_address(address):
    """Validate Ethereum address format"""
    if not address or not isinstance(address, str):
        return False
    
    address = address.strip()
    if not address.startswith('0x') or len(address) != 42:
        return False
    
    # Basic hex validation
    try:
        int(address, 16)
    except ValueError:
        return False
    
    return True

def checksum_address(address):
    """Convert address to checksum format"""
    if validate_eth_address(address):
        return Web3.to_checksum_address(address)
    return address