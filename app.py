"""
Blockchain-Based Land Registration System
Unified Flask Application

This is the main entry point for the Land Registration DApp.
It serves all roles: Users (Sellers/Buyers), Revenue Officers, and Admins.
"""

from flask import (
    Flask, jsonify, render_template, request,
    Response, redirect, session, url_for
)
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import json
import os

# Our utility modules
from utils.blockchain import get_contract_details, map_revenue_dept_to_employee, load_config
from utils.db import (
    fs, property_docs_collection, employees_collection,
    notifications_collection, audit_logs_collection,
    transactions_collection, land_records_collection,
    ownership_history_collection, users_collection,
    verification_requests_collection,
    log_audit, create_notification, log_transaction
)

# Load config
config = load_config()

# Flask app
app = Flask(
    __name__,
    static_url_path='/static',
    static_folder='static',
    template_folder='templates'
)
app.secret_key = config["Secret_Key"]
app.config['MAX_CONTENT_LENGTH'] = config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)

# Ensure upload directory exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.get("UPLOAD_FOLDER", "uploads"))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Network chain ID as string for contract lookups
NETWORK_CHAIN_ID = str(config["NETWORK_CHAIN_ID"])


# ============================================================
#                    PUBLIC ROUTES
# ============================================================

@app.route('/')
def index():
    """Landing / Home page"""
    return render_template('index.html')


@app.route('/about')
def about():
    """About the project page"""
    return render_template('about.html')


@app.route('/properties')
def public_properties():
    """Public property listing — shows verified & on-sale properties"""
    return render_template('properties.html')


@app.route('/login')
def login_page():
    """Unified login page for officers and admins"""
    return render_template('login.html')


@app.route('/register')
def register_page():
    """User registration page (MetaMask-based)"""
    return render_template('register.html')


# ============================================================
#                    USER ROUTES
# ============================================================

@app.route('/user/dashboard')
def user_dashboard():
    """User dashboard — shows overview stats and properties"""
    return render_template('user/dashboard.html')


@app.route('/user/register-land')
def register_land():
    """Register new land form"""
    return render_template('user/register_land.html')


@app.route('/user/my-properties')
def my_properties():
    """User's registered properties"""
    return render_template('user/my_properties.html')


@app.route('/user/available-to-buy')
def available_to_buy():
    """Browse properties available for purchase"""
    return render_template('user/available_to_buy.html')


@app.route('/user/my-sales')
def my_sales():
    """Sales created by user (as seller)"""
    return render_template('user/my_sales.html')


@app.route('/user/my-purchases')
def my_purchases():
    """Purchase requests made by user (as buyer)"""
    return render_template('user/my_purchases.html')


@app.route('/user/transactions')
def user_transactions():
    """Transaction history for the user"""
    return render_template('user/transaction_history.html')


# ============================================================
#                    REVENUE OFFICER ROUTES
# ============================================================

@app.route('/officer/dashboard')
def officer_dashboard():
    """Revenue officer dashboard — pending verifications"""
    if 'user_id' not in session or session.get('role') != 'officer':
        return redirect('/login')
    return render_template('officer/dashboard.html')


@app.route('/officer/login', methods=['POST'])
def officer_login():
    """Revenue officer login"""
    employee_id = request.form.get('employeeId')
    password = request.form.get('password')

    user = employees_collection.find_one({"employeeId": employee_id})

    if user and check_password_hash(user['password'], password):
        session['user_id'] = str(user['_id'])
        session['role'] = 'officer'
        session['emp_name'] = user.get('fname', '')
        session['revenue_dept_id'] = user.get('revenueDeptId', '')

        log_audit("Officer Login", employee_id, "Revenue officer logged in", "auth")

        return jsonify({
            'status': 1,
            'msg': 'Login Success',
            'revenueDepartmentId': user.get('revenueDeptId', ''),
            'empName': user.get('fname', '')
        })
    else:
        return jsonify({'status': 0, 'msg': 'Invalid credentials'})


# ============================================================
#                    ADMIN ROUTES
# ============================================================

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard — system overview"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    return render_template('admin/dashboard.html')


@app.route('/admin/login', methods=['POST'])
def admin_login():
    """Admin login"""
    admin_address = request.form.get('adminAddress')
    password = request.form.get('password')

    admin = employees_collection.find_one({'adminAddress': admin_address})

    if admin and check_password_hash(admin['password'], password):
        session['user_id'] = str(admin['_id'])
        session['role'] = 'admin'

        log_audit("Admin Login", admin_address, "Admin logged in", "auth")

        return jsonify({'status': 1, 'msg': 'Admin Login Success'})
    else:
        return jsonify({'status': 0, 'msg': 'Invalid credentials'})


@app.route('/admin/manage-officers')
def manage_officers():
    """Manage revenue officers"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    return render_template('admin/manage_officers.html')


@app.route('/admin/add-officer', methods=['POST'])
def add_officer():
    """Add a new revenue officer"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'status': 0, 'msg': 'Login Required'})

    employee_id = request.form.get('empAddress')
    password = request.form.get('password')
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    revenue_dept_id = request.form.get('revenueDeptId')

    emp = {
        "employeeId": employee_id,
        "password": generate_password_hash(password),
        "fname": fname,
        "lname": lname,
        "revenueDeptId": revenue_dept_id,
        "created_at": datetime.utcnow()
    }

    try:
        employees_collection.insert_one(emp)

        # Map revenue department ID to employee on blockchain
        result = map_revenue_dept_to_employee(revenue_dept_id, employee_id)

        if result:
            log_audit("Add Officer", session.get('user_id', ''),
                       f"Added officer {fname} {lname} for dept {revenue_dept_id}", "admin")
            return jsonify({
                'status': 1,
                'msg': f"Officer '{fname}' added successfully"
            })
        else:
            return jsonify({
                'status': 0,
                'msg': 'Blockchain transaction failed'
            })

    except Exception as e:
        return jsonify({'status': 0, 'msg': str(e)})


@app.route('/admin/all-properties')
def admin_all_properties():
    """View all land records"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    return render_template('admin/all_properties.html')


@app.route('/admin/all-transactions')
def admin_all_transactions():
    """View all transactions"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    return render_template('admin/all_transactions.html')


@app.route('/admin/manage-users')
def admin_manage_users():
    """Manage registered users"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    return render_template('admin/manage_users.html')


@app.route('/admin/audit-logs')
def admin_audit_logs():
    """View audit logs"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    return render_template('admin/audit_logs.html')


@app.route('/admin/reports')
def admin_reports():
    """View and generate reports"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    return render_template('admin/reports.html')


# ============================================================
#                    API ROUTES
# ============================================================

@app.route('/api/contract-details')
def api_contract_details():
    """Return contract ABI and addresses for frontend Web3 integration"""
    try:
        contracts = get_contract_details()
        return jsonify(contracts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/upload-docs', methods=['POST'])
def upload_docs():
    """Upload property documents to GridFS"""
    try:
        registration_docs = request.files.get('propertyDocs')
        owner = request.form.get('owner')
        property_id = request.form.get('propertyId')

        if not registration_docs or not owner or not property_id:
            return jsonify({'status': 'error', 'msg': 'Missing required fields'})

        filename = f"{owner}_{property_id}.pdf"
        file_id = fs.put(registration_docs, filename=filename)

        property_docs_collection.insert_one({
            "Owner": owner,
            "Property_Id": property_id,
            filename: file_id,
            "uploaded_at": datetime.utcnow()
        })

        log_audit("Upload Document", owner,
                   f"Uploaded docs for property {property_id}", "property")

        return jsonify({'status': 'success', 'fileId': str(file_id)})

    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})


@app.route('/api/property-doc/<property_id>')
def get_property_doc(property_id):
    """Serve property PDF document"""
    try:
        prop = property_docs_collection.find_one({"Property_Id": str(property_id)})
        if not prop:
            return jsonify({"status": 0, "reason": "No property matched with ID"}), 404

        filename = f"{prop['Owner']}_{prop['Property_Id']}.pdf"
        file = fs.get(prop[filename])

        response = Response(file, content_type='application/pdf')
        response.headers['Content-Disposition'] = f'inline; filename="{file.filename}"'
        return response

    except Exception as e:
        return jsonify({"status": 0, "reason": str(e)}), 500


@app.route('/api/log-transaction', methods=['POST'])
def api_log_transaction():
    """Log a blockchain transaction to MongoDB"""
    try:
        data = request.get_json()
        log_transaction(
            tx_hash=data.get('txHash', ''),
            tx_type=data.get('txType', ''),
            from_addr=data.get('fromAddress', ''),
            to_addr=data.get('toAddress', ''),
            property_id=data.get('propertyId', ''),
            amount=data.get('amount', 0),
            details=data.get('details', '')
        )
        return jsonify({'status': 1, 'msg': 'Transaction logged'})
    except Exception as e:
        return jsonify({'status': 0, 'msg': str(e)})


@app.route('/api/notifications/<address>')
def api_get_notifications(address):
    """Get notifications for a user by wallet address"""
    try:
        notifs = list(notifications_collection.find(
            {"recipient": address},
            {"_id": 0}
        ).sort("timestamp", -1).limit(20))

        # Convert datetime to string for JSON
        for n in notifs:
            if 'timestamp' in n:
                n['timestamp'] = n['timestamp'].isoformat()

        return jsonify({"status": 1, "notifications": notifs})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})


@app.route('/api/transactions/<address>')
def api_get_transactions(address):
    """Get transaction history for a user"""
    try:
        txns = list(transactions_collection.find(
            {"$or": [{"from_address": address}, {"to_address": address}]},
            {"_id": 0}
        ).sort("timestamp", -1).limit(50))

        for t in txns:
            if 'timestamp' in t:
                t['timestamp'] = t['timestamp'].isoformat()

        return jsonify({"status": 1, "transactions": txns})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})


@app.route('/api/all-transactions')
def api_all_transactions():
    """Get all transactions (admin only)"""
    try:
        txns = list(transactions_collection.find(
            {}, {"_id": 0}
        ).sort("timestamp", -1).limit(200))

        for t in txns:
            if 'timestamp' in t:
                t['timestamp'] = t['timestamp'].isoformat()

        return jsonify({"status": 1, "transactions": txns})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})


@app.route('/api/audit-logs')
def api_audit_logs():
    """Get audit logs (admin only)"""
    try:
        logs = list(audit_logs_collection.find(
            {}, {"_id": 0}
        ).sort("timestamp", -1).limit(200))

        for l in logs:
            if 'timestamp' in l:
                l['timestamp'] = l['timestamp'].isoformat()

        return jsonify({"status": 1, "logs": logs})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})


@app.route('/api/ownership-history/<property_id>')
def api_ownership_history(property_id):
    """Get ownership history for a property"""
    try:
        history = list(ownership_history_collection.find(
            {"property_id": property_id},
            {"_id": 0}
        ).sort("timestamp", -1))

        for h in history:
            if 'timestamp' in h:
                h['timestamp'] = h['timestamp'].isoformat()

        return jsonify({"status": 1, "history": history})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})


@app.route('/api/stats')
def api_stats():
    """Get system statistics for admin dashboard"""
    try:
        stats = {
            "total_users": users_collection.count_documents({}),
            "total_officers": employees_collection.count_documents({"employeeId": {"$exists": True}}),
            "total_properties": property_docs_collection.count_documents({}),
            "total_transactions": transactions_collection.count_documents({}),
        }
        return jsonify({"status": 1, "stats": stats})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})


# ============================================================
#                    SESSION / AUTH ROUTES
# ============================================================

@app.route('/logout')
def logout():
    """Clear session and redirect to home"""
    role = session.get('role', '')
    session.clear()
    return redirect('/')


# ============================================================
#                    ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ============================================================
#                    STARTUP
# ============================================================

if __name__ == '__main__':
    admin_address = config.get("Address_Used_To_Deploy_Contract")
    admin_password = config.get("Admin_Password")

    # Ensure admin account exists
    if admin_address and admin_password:
        admin = employees_collection.find_one({'adminAddress': admin_address})
        if admin is None:
            print("\n[SETUP] Adding Admin account to database...")
            admin_doc = {
                "adminAddress": admin_address,
                "password": generate_password_hash(admin_password),
                "created_at": datetime.utcnow()
            }
            result = employees_collection.insert_one(admin_doc)
            if result.inserted_id:
                print("[SETUP] Admin account added successfully")
            else:
                print("[SETUP] Failed to add admin account")
                exit(1)
        else:
            print("[SETUP] Admin account already exists")

    print("\n" + "=" * 50)
    print("  Land Registration System - Blockchain DApp")
    print("  Server: http://localhost:5000")
    print("=" * 50 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
