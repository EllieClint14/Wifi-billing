from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import random
import string
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wifi_billing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)        
    price = db.Column(db.Float, nullable=False)            
    duration_mins = db.Column(db.Integer, nullable=False)  
    speed_limit = db.Column(db.String(20), nullable=False) 

class Voucher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(12), unique=True, nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activated_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    transaction_reference = db.Column(db.String(50), nullable=True)

def generate_random_code(length=6):
    characters = string.digits + "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return ''.join(random.choice(characters) for _ in range(length))

# --- API ROUTES ---
@app.route('/api/packages', methods=['GET'])
def get_packages():
    packages = Package.query.all()
    return jsonify([{
        "id": p.id, "name": p.name, "price": p.price, 
        "duration_mins": p.duration_mins, "speed_limit": p.speed_limit
    } for p in packages])

@app.route('/api/payment/callback', methods=['POST'])
def payment_callback():
    payment_data = request.json
    result_code = payment_data.get('result_code') 
    amount_paid = float(payment_data.get('amount'))
    transaction_ref = payment_data.get('transaction_id')
    
    if result_code != 0:
        return jsonify({"status": "Failed", "message": "Payment rejected"}), 400

    package = Package.query.filter_by(price=amount_paid).first()
    if not package:
        return jsonify({"status": "Error", "message": "No matching package profile found."}), 404

    voucher_code = generate_random_code(6)
    new_voucher = Voucher(code=voucher_code, package_id=package.id, transaction_reference=transaction_ref)
    db.session.add(new_voucher)
    db.session.commit()

    return jsonify({
        "status": "Success",
        "voucher_code": voucher_code,
        "profile": package.name,
        "speed_limit": package.speed_limit
    }), 200

@app.route('/api/voucher/activate', methods=['POST'])
def activate_voucher():
    data = request.json
    input_code = data.get('code', '').upper().strip()
    
    voucher = Voucher.query.filter_by(code=input_code).first()
    if not voucher:
        return jsonify({"status": "Denied", "message": "Invalid voucher code."}), 404
        
    package = Package.query.get(voucher.package_id)
    
    if voucher.is_used:
        if datetime.utcnow() > voucher.expires_at:
            return jsonify({"status": "Expired", "message": "Voucher run out of time."}), 410
        
        time_left = (voucher.expires_at - datetime.utcnow()).total_seconds()
        return jsonify({
            "status": "Authorized",
            "time_remaining_seconds": int(time_left),
            "speed_limit": package.speed_limit
        }), 200

    now = datetime.utcnow()
    expiration_time = now + timedelta(minutes=package.duration_mins)
    
    voucher.is_used = True
    voucher.activated_at = now
    voucher.expires_at = expiration_time
    db.session.commit()

    return jsonify({
        "status": "Authorized",
        "time_limit_minutes": package.duration_mins,
        "speed_limit": package.speed_limit
    }), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Clean data setup: Seed the clean database profiles matching the new clean options
        if not Package.query.first():
            db.session.add_all([
                Package(name="30 Minutes", price=5.0, duration_mins=30, speed_limit="3M/3M"),
                Package(name="1 Hour", price=10.0, duration_mins=60, speed_limit="3M/3M"),
                Package(name="3 Hours", price=20.0, duration_mins=180, speed_limit="4M/4M"),
                Package(name="12 Hours", price=45.0, duration_mins=720, speed_limit="4M/4M"),
                Package(name="24 Hours", price=60.0, duration_mins=1440, speed_limit="5M/5M"),
                Package(name="1 Week", price=250.0, duration_mins=10080, speed_limit="6M/6M"),
                Package(name="1 Month", price=850.0, duration_mins=43200, speed_limit="8M/8M")
            ])
            db.session.commit()
            
    app.run(debug=True, port=5000)