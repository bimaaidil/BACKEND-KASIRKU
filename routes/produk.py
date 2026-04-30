from flask import Blueprint, request, jsonify
from firebase_config import db

# Ganti definisi Blueprint agar url_prefix tidak butuh slash tambahan
produk_bp = Blueprint('produk', __name__)

# --- PERBAIKAN: Gunakan string kosong '' bukan '/' ---

# 1. AMBIL SEMUA PRODUK (GET)
@produk_bp.route('', methods=['GET'])
def get_produk():
    try:
        products_ref = db.collection('products')
        docs = products_ref.stream()
        result = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            result.append(data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 2. TAMBAH PRODUK (POST)
@produk_bp.route('', methods=['POST'])
def add_produk():
    try:
        data = request.json
        # Validasi sederhana
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        db.collection('products').add(data)
        return jsonify({"message": "Produk berhasil ditambahkan"}), 201
    except Exception as e:
        print(f"Error adding product: {e}") # Cetak error di terminal backend
        return jsonify({"error": str(e)}), 500

# 3. HAPUS PRODUK (DELETE) - Butuh ID, jadi pakai '/<id>'
@produk_bp.route('/<id>', methods=['DELETE'])
def delete_produk(id):
    try:
        db.collection('products').document(id).delete()
        return jsonify({"message": "Produk berhasil dihapus"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 4. EDIT PRODUK (PUT)
@produk_bp.route('/<id>', methods=['PUT'])
def update_produk(id):
    try:
        data = request.json
        db.collection('products').document(id).update(data)
        return jsonify({"message": "Produk berhasil diupdate"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500