"""
Database utility module for Land Registration System.
Handles MongoDB connection and collection access.
"""

from pymongo import MongoClient
import gridfs
from datetime import datetime
import os
import json

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load config
config_path = os.path.join(BASE_DIR, "config.json")
with open(config_path, "r") as f:
    _config = json.load(f)

# MongoDB connection
_client = MongoClient(_config["Mongo_Db_Url"])

# Databases
land_registry_db = _client.LandRegistry
revenue_dept_db = _client.Revenue_Dept

# GridFS for file storage
fs = gridfs.GridFS(land_registry_db)

# ============ Collections ============

# User-related
users_collection = land_registry_db.users
employees_collection = revenue_dept_db.Employees

# Property-related
property_docs_collection = land_registry_db.Property_Docs
land_records_collection = land_registry_db.land_records

# Transaction-related
transactions_collection = land_registry_db.transactions
ownership_history_collection = land_registry_db.ownership_history

# Verification
verification_requests_collection = land_registry_db.verification_requests

# System
notifications_collection = land_registry_db.notifications
audit_logs_collection = land_registry_db.audit_logs


# ============ Helper Functions ============

def log_audit(action, user, details="", category="general"):
    """Log an action to the audit trail."""
    audit_logs_collection.insert_one({
        "action": action,
        "user": user,
        "details": details,
        "category": category,
        "timestamp": datetime.utcnow()
    })


def create_notification(recipient, title, message, notif_type="info"):
    """Create a notification for a user."""
    notifications_collection.insert_one({
        "recipient": recipient,
        "title": title,
        "message": message,
        "type": notif_type,
        "read": False,
        "timestamp": datetime.utcnow()
    })


def log_transaction(tx_hash, tx_type, from_addr, to_addr="", property_id="", amount=0, details=""):
    """Log a blockchain transaction to MongoDB."""
    transactions_collection.insert_one({
        "tx_hash": tx_hash,
        "tx_type": tx_type,
        "from_address": from_addr,
        "to_address": to_addr,
        "property_id": property_id,
        "amount": amount,
        "details": details,
        "timestamp": datetime.utcnow()
    })


def log_ownership_change(property_id, from_addr, to_addr, tx_hash=""):
    """Record ownership transfer in history."""
    ownership_history_collection.insert_one({
        "property_id": property_id,
        "from_address": from_addr,
        "to_address": to_addr,
        "tx_hash": tx_hash,
        "timestamp": datetime.utcnow()
    })
