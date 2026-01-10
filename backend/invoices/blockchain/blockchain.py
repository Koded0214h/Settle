"""
Blockchain interaction module for Settle
"""
import json
import os
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from django.conf import settings
import logging
import requests
from decimal import Decimal

logger = logging.getLogger(__name__)

# Initialize Web3
try:
    web3 = Web3(Web3.HTTPProvider(settings.SCROLL_RPC_URL))
    if not web3.is_connected():
        logger.warning(f"Failed to connect to Web3 at {settings.SCROLL_RPC_URL}")
        web3 = None
except Exception as e:
    logger.error(f"Error initializing Web3: {e}")
    web3 = None

# Load ABIs from JSON files
def load_abi_from_file(filename):
    """Load ABI from JSON file"""
    try:
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        abis_dir = os.path.join(current_dir, 'abis')
        filepath = os.path.join(abis_dir, filename)
        
        if not os.path.exists(filepath):
            logger.error(f"ABI file not found: {filepath}")
            return None
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            # Extract ABI from artifact if needed
            if 'abi' in data:
                return data['abi']
            elif isinstance(data, list):  # Already an ABI array
                return data
            return data
    except Exception as e:
        logger.error(f"Error loading ABI from {filename}: {e}")
        return None

# Load ABIs
INVOICE_CONTRACT_ABI = load_abi_from_file('SettleInvoicing.json')
USDC_CONTRACT_ABI = load_abi_from_file('MockUSDC.json')

if not INVOICE_CONTRACT_ABI:
    logger.error("Failed to load SettleInvoicing ABI")
if not USDC_CONTRACT_ABI:
    logger.error("Failed to load MockUSDC ABI")

def get_invoice_contract():
    """Get invoice contract instance"""
    if not web3:
        logger.error("Web3 not initialized")
        return None
    
    contract_address = getattr(settings, 'INVOICE_CONTRACT_ADDRESS', None)
    if not contract_address:
        logger.error("INVOICE_CONTRACT_ADDRESS not set in settings")
        return None
    
    if not INVOICE_CONTRACT_ABI:
        logger.error("Invoice contract ABI not loaded")
        return None
    
    try:
        return web3.eth.contract(
            address=web3.to_checksum_address(contract_address),
            abi=INVOICE_CONTRACT_ABI
        )
    except Exception as e:
        logger.error(f"Error creating invoice contract instance: {e}")
        return None

def get_usdc_contract():
    """Get USDC contract instance"""
    if not web3:
        logger.error("Web3 not initialized")
        return None
    
    contract_address = getattr(settings, 'USDC_CONTRACT_ADDRESS', None)
    if not contract_address:
        logger.error("USDC_CONTRACT_ADDRESS not set in settings")
        return None
    
    if not USDC_CONTRACT_ABI:
        logger.error("USDC contract ABI not loaded")
        return None
    
    try:
        return web3.eth.contract(
            address=web3.to_checksum_address(contract_address),
            abi=USDC_CONTRACT_ABI
        )
    except Exception as e:
        logger.error(f"Error creating USDC contract instance: {e}")
        return None

def create_invoice_on_blockchain(invoice_data):
    """
    Create invoice on blockchain
    
    Args:
        invoice_data: {
            'freelancer_address': str,
            'amount': int (in wei, 6 decimals for USDC),
            'due_date': int (timestamp),
            'ipfs_hash': str
        }
    """
    if not web3:
        logger.error("Web3 not initialized")
        return None
    
    try:
        contract = get_invoice_contract()
        if not contract:
            return None
        
        # Prepare transaction
        tx = contract.functions.registerInvoice(
            invoice_data['amount'],
            invoice_data['due_date'],
            invoice_data['ipfs_hash']
        ).build_transaction({
            'from': invoice_data['freelancer_address'],
            'nonce': web3.eth.get_transaction_count(invoice_data['freelancer_address']),
            'gas': 200000,
            'gasPrice': web3.to_wei('1', 'gwei'),
            'chainId': getattr(settings, 'SCROLL_CHAIN_ID', 534351),
        })
        
        return tx
    
    except Exception as e:
        logger.error(f"Error creating invoice on blockchain: {e}")
        return None

def pay_invoice_on_blockchain(invoice_id, payer_address, usdc_amount):
    """
    Pay invoice on blockchain
    
    Args:
        invoice_id: int
        payer_address: str
        usdc_amount: int (in wei, 6 decimals)
    """
    if not web3:
        logger.error("Web3 not initialized")
        return None
    
    try:
        contract = get_invoice_contract()
        usdc_contract = get_usdc_contract()
        
        if not contract or not usdc_contract:
            return None
        
        # First approve USDC spending
        approve_tx = usdc_contract.functions.approve(
            contract.address,
            usdc_amount
        ).build_transaction({
            'from': payer_address,
            'nonce': web3.eth.get_transaction_count(payer_address),
            'gas': 100000,
            'gasPrice': web3.to_wei('1', 'gwei'),
            'chainId': getattr(settings, 'SCROLL_CHAIN_ID', 534351),
        })
        
        # Then pay invoice
        pay_tx = contract.functions.payInvoice(
            invoice_id,
            usdc_contract.address
        ).build_transaction({
            'from': payer_address,
            'nonce': web3.eth.get_transaction_count(payer_address) + 1,
            'gas': 200000,
            'gasPrice': web3.to_wei('1', 'gwei'),
            'chainId': getattr(settings, 'SCROLL_CHAIN_ID', 534351),
        })
        
        return {
            'approve_tx': approve_tx,
            'pay_tx': pay_tx
        }
    
    except Exception as e:
        logger.error(f"Error creating payment transaction: {e}")
        return None

def create_user_operation(sender, nonce, init_code, call_data, call_gas_limit,
                         verification_gas_limit, pre_verification_gas,
                         max_fee_per_gas, max_priority_fee_per_gas,
                         paymaster_and_data, signature):
    """
    Create ERC-4337 User Operation
    """
    user_op = {
        'sender': sender,
        'nonce': nonce,
        'initCode': init_code,
        'callData': call_data,
        'callGasLimit': call_gas_limit,
        'verificationGasLimit': verification_gas_limit,
        'preVerificationGas': pre_verification_gas,
        'maxFeePerGas': max_fee_per_gas,
        'maxPriorityFeePerGas': max_priority_fee_per_gas,
        'paymasterAndData': paymaster_and_data,
        'signature': signature,
    }
    
    return user_op

def sponsor_gas_with_paymaster(user_op, paymaster_and_data):
    """
    Add paymaster sponsorship to user operation
    """
    try:
        paymaster_url = getattr(settings, 'PAYMASTER_URL', None)
        if not paymaster_url:
            logger.error("PAYMASTER_URL not configured")
            return None
        
        response = requests.post(
            f"{paymaster_url}/sponsor",
            json={
                'userOp': user_op,
                'paymasterAndData': paymaster_and_data,
                'chainId': getattr(settings, 'SCROLL_CHAIN_ID', 534351),
                'entryPoint': getattr(settings, 'ENTRYPOINT_ADDRESS', '0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789'),
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json().get('sponsoredUserOp')
        else:
            logger.error(f"Paymaster error: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error with paymaster: {e}")
        return None

def submit_user_operation_to_bundler(user_op):
    """
    Submit user operation to bundler
    """
    try:
        bundler_url = getattr(settings, 'BUNDLER_URL', None)
        if not bundler_url:
            logger.error("BUNDLER_URL not configured")
            return None
        
        response = requests.post(
            f"{bundler_url}/rpc",
            json={
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'eth_sendUserOperation',
                'params': [user_op, getattr(settings, 'ENTRYPOINT_ADDRESS', '0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789')],
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                return result['result']  # userOpHash
            elif 'error' in result:
                logger.error(f"Bundler error: {result['error']}")
                return None
        
        return None
    
    except Exception as e:
        logger.error(f"Error with bundler: {e}")
        return None

def check_user_op_status_from_bundler(user_op_hash):
    """
    Check status of user operation from bundler
    """
    try:
        bundler_url = getattr(settings, 'BUNDLER_URL', None)
        if not bundler_url:
            logger.error("BUNDLER_URL not configured")
            return None
        
        response = requests.post(
            f"{bundler_url}/rpc",
            json={
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'eth_getUserOperationByHash',
                'params': [user_op_hash],
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                return result['result']
        
        return None
    
    except Exception as e:
        logger.error(f"Error checking user op status: {e}")
        return None

def get_invoice_from_contract(invoice_id):
    """
    Get invoice details from blockchain
    """
    if not web3:
        logger.error("Web3 not initialized")
        return None
    
    try:
        contract = get_invoice_contract()
        if not contract:
            return None
        
        invoice_data = contract.functions.getInvoice(invoice_id).call()
        
        return {
            'freelancer': invoice_data[0],
            'client': invoice_data[1],
            'amount': invoice_data[2],
            'due_date': invoice_data[3],
            'is_paid': invoice_data[4],
            'invoice_uri': invoice_data[5],
        }
    
    except Exception as e:
        logger.error(f"Error getting invoice from contract: {e}")
        return None

def convert_usdc_to_wei(amount, decimals=6):
    """Convert USDC amount to wei"""
    try:
        return int(Decimal(str(amount)) * (10 ** decimals))
    except Exception as e:
        logger.error(f"Error converting USDC to wei: {e}")
        return 0

def convert_wei_to_usdc(amount, decimals=6):
    """Convert wei to USDC amount"""
    try:
        return Decimal(str(amount)) / (10 ** decimals)
    except Exception as e:
        logger.error(f"Error converting wei to USDC: {e}")
        return Decimal('0')

def get_wallet_balance(address, token_address=None):
    """Get token balance for a wallet"""
    if not web3:
        logger.error("Web3 not initialized")
        return None
    
    try:
        if token_address:
            # ERC20 token balance
            usdc_contract = get_usdc_contract()
            if not usdc_contract:
                return None
            balance = usdc_contract.functions.balanceOf(address).call()
            decimals = usdc_contract.functions.decimals().call()
            return convert_wei_to_usdc(balance, decimals)
        else:
            # Native token balance
            balance = web3.eth.get_balance(address)
            return web3.from_wei(balance, 'ether')
    
    except Exception as e:
        logger.error(f"Error getting wallet balance: {e}")
        return None

def listen_for_invoice_events():
    """Listen for blockchain events"""
    if not web3:
        logger.error("Web3 not initialized")
        return []
    
    try:
        contract = get_invoice_contract()
        if not contract:
            return []
        
        # Get latest block
        latest_block = web3.eth.block_number
        
        # Filter for InvoiceCreated events
        invoice_created_filter = contract.events.InvoiceCreated.create_filter(
            fromBlock=latest_block - 1000,
            toBlock='latest'
        )
        
        # Filter for InvoicePaid events
        invoice_paid_filter = contract.events.InvoicePaid.create_filter(
            fromBlock=latest_block - 1000,
            toBlock='latest'
        )
        
        events = invoice_created_filter.get_all_entries()
        events += invoice_paid_filter.get_all_entries()
        
        return events
    
    except Exception as e:
        logger.error(f"Error listening for events: {e}")
        return []