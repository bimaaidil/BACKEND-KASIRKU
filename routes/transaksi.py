from flask import Blueprint, request, jsonify
from firebase_config import db
from datetime import datetime

# INI YANG DICARI OLEH APP.PY
transaksi_bp = Blueprint('transaksi', __name__)
COLLECTION_NAME = 'transactions'

# 1. SIMPAN TRANSAKSI (POST)
@transaksi_bp.route('', methods=['POST'])
def add_transaction():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Data kosong"}), 400

        # Tambahkan timestamp server
        data['timestamp'] = datetime.now()
        data['date'] = datetime.now().strftime("%Y-%m-%d") # Biar mudah difilter per hari
        
        # Simpan ke Firestore
        db.collection(COLLECTION_NAME).add(data)
        
        return jsonify({"message": "Transaksi berhasil disimpan!"}), 201
    except Exception as e:
        print(f"Error Transaksi: {e}")
        return jsonify({"error": str(e)}), 500

# 2. AMBIL RIWAYAT TRANSAKSI (GET)
@transaksi_bp.route('', methods=['GET'])
def get_transactions():
    try:
        docs = db.collection(COLLECTION_NAME).order_by('timestamp', direction='DESCENDING').stream()
        result = []
        for doc in docs:
            t = doc.to_dict()
            t['id'] = doc.id
            if 'timestamp' in t:
                t['timestamp'] = str(t['timestamp'])
            result.append(t)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500