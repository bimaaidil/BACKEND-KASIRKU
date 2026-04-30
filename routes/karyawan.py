from flask import Blueprint, request, jsonify
from firebase_config import db

karyawan_bp = Blueprint('karyawan', __name__)

# Gunakan nama koleksi 'employees' di database sesuai konfigurasi Bima
COLLECTION_NAME = 'employees'

# 1. AMBIL SEMUA KARYAWAN (GET)
@karyawan_bp.route('', methods=['GET'])
def get_karyawan():
    try:
        docs = db.collection(COLLECTION_NAME).stream()
        result = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            result.append(data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 2. TAMBAH KARYAWAN (POST)
@karyawan_bp.route('', methods=['POST'])
def add_karyawan():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Data kosong"}), 400
            
        # Menambahkan data ke Firestore
        db.collection(COLLECTION_NAME).add(data)
        return jsonify({"message": "Karyawan berhasil ditambahkan"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 3. EDIT KARYAWAN (PUT) - Untuk Update Data Profil
@karyawan_bp.route('/<id>', methods=['PUT'])
def update_karyawan(id):
    try:
        data = request.json
        db.collection(COLLECTION_NAME).document(id).update(data)
        return jsonify({"message": "Data karyawan diupdate"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 4. VERIFIKASI STATUS KARYAWAN (PUT + OPTIONS)
# Endpoint ini yang dipanggil oleh tombol "Verifikasi" di React
@karyawan_bp.route('/<id>/status', methods=['PUT', 'OPTIONS'])
def update_status(id):
    # Menangani Preflight Request dari Browser (CORS)
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.json
        new_status = data.get('status') # Mengambil 'AKTIF' dari body request
        
        if not new_status:
            return jsonify({"error": "Status tidak ditemukan"}), 400

        # Update hanya field 'status' di Firestore
        db.collection(COLLECTION_NAME).document(id).update({
            'status': new_status
        })
        
        return jsonify({"message": f"Karyawan berhasil diverifikasi menjadi {new_status}"}), 200
    except Exception as e:
        print(f"Error Update Status: {str(e)}")
        return jsonify({"error": "Gagal update status di database"}), 500

# 5. HAPUS KARYAWAN (DELETE)
@karyawan_bp.route('/<id>', methods=['DELETE'])
def delete_karyawan(id):
    try:
        db.collection(COLLECTION_NAME).document(id).delete()
        return jsonify({"message": "Karyawan dihapus"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500