"""
Blockchain utility module for Land Registration System.
Handles Web3 connection, contract loading, and blockchain transactions.

Note: Web3.py has compatibility issues with Python 3.14+.
The blockchain integration primarily runs on the frontend via Web3.js.
This module provides fallback server-side utilities.
"""

import json
import os

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Try to import web3 — may fail on Python 3.14+
try:
    from web3 import Web3
    WEB3_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Web3.py not available: {e}")
    print("[WARNING] Server-side blockchain calls disabled. Frontend Web3.js still works.")
    WEB3_AVAILABLE = False


def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(BASE_DIR, "config.json")
    with open(config_path, "r") as f:
        return json.load(f)


def get_web3_instance():
    """Create and return a Web3 instance connected to Ganache."""
    if not WEB3_AVAILABLE:
        return None
    config = load_config()
    ganache_url = config["Ganache_Url"]
    web3 = Web3(Web3.HTTPProvider(ganache_url))
    return web3


def get_contract_json(contract_name):
    """
    Load compiled contract JSON from Truffle build artifacts.
    Uses absolute paths to avoid CWD issues.
    """
    contract_path = os.path.join(
        BASE_DIR,
        "Major-Project",
        "Smart_contracts",
        "build",
        "contracts",
        f"{contract_name}.json"
    )
    with open(contract_path, "r") as f:
        return json.load(f)


def get_contract_details():
    """
    Fetch contract ABI and deployed address for all contracts.
    Returns dict with Users, LandRegistry, TransferOwnership details.
    """
    config = load_config()
    network_id = str(config["NETWORK_CHAIN_ID"])

    contracts = {}
    contract_names = {
        "Users": "Users",
        "LandRegistry": "LandRegistry",
        "TransferOwnership": "TransferOwnerShip"
    }

    for key, filename in contract_names.items():
        try:
            contract_json = get_contract_json(filename)
            contracts[key] = {
                "address": contract_json["networks"][network_id]["address"],
                "abi": contract_json["abi"]
            }
        except (KeyError, FileNotFoundError) as e:
            print(f"Warning: Could not load contract {filename}: {e}")
            contracts[key] = {"address": None, "abi": None}

    return contracts


def map_revenue_dept_to_employee(revenue_dept_id, employee_address):
    """
    Execute blockchain transaction to map a revenue department ID
    to an employee's Ethereum address.
    """
    if not WEB3_AVAILABLE:
        print("[WARNING] Web3 not available. Cannot execute blockchain transaction.")
        print("[WARNING] Please map revenue dept manually via Truffle console.")
        return True  # Return True so the MongoDB record is still created

    config = load_config()
    web3 = get_web3_instance()

    # Set deployer as default account
    deployer_address = config["Address_Used_To_Deploy_Contract"]
    web3.eth.default_account = deployer_address

    network_id = str(config["NETWORK_CHAIN_ID"])

    # Load LandRegistry contract
    contract_json = get_contract_json("LandRegistry")
    contract_abi = contract_json["abi"]
    contract_address = contract_json["networks"][network_id]["address"]

    contract = web3.eth.contract(abi=contract_abi, address=contract_address)

    try:
        txn_hash = contract.functions.mapRevenueDeptIdToEmployee(
            int(revenue_dept_id),
            employee_address
        ).transact({'from': deployer_address})

        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(txn_hash)

        return receipt['status'] == 1
    except Exception as e:
        print(f"Blockchain transaction error: {e}")
        return False
