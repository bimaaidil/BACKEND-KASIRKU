# routes/kas.py
from flask import Blueprint, request, jsonify
from firebase_config import db
import time

kas_bp = Blueprint('kas', __name__)

# 1. AMBIL SEMUA DATA KAS (GET)
@kas_bp.route('', methods=['GET'])
def get_kas():
    try:
        kas_ref = db.collection('kas_logs')
        # Urutkan berdasarkan id/timestamp secara descending (terbaru di atas)
        docs = kas_ref.order_by('id', direction='DESCENDING').stream()
        
        result = []
        for doc in docs:
            data = doc.to_dict()
            data['doc_id'] = doc.id # Ambil ID dokumen asli Firebase jika dibutuhkan
            result.append(data)
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 2. SIMPAN TRANSAKSI KAS BARU (POST)
@kas_bp.route('', methods=['POST'])
def add_kas():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Data tidak boleh kosong"}), 400
            
        # Simpan data ke koleksi kas_logs
        db.collection('kas_logs').add(data)
        return jsonify({"message": "Data kas berhasil disimpan ke cloud"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500