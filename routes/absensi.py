# backend/routes/absensi.py
from flask import Blueprint, request, jsonify
from firebase_config import db
from datetime import datetime

absensi_bp = Blueprint('absensi', __name__)
COLLECTION_NAME = 'attendance'

@absensi_bp.route('/clock-in', methods=['POST'])
def clock_in():
    try:
        data = request.json
        employee_id = data.get('employee_id')
        employee_name = data.get('employee_name')
        jenis_absen = data.get('jenis_absen', 'Reguler') 
        
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M:%S')

        # Cek duplikat
        existing = db.collection(COLLECTION_NAME)\
            .where('employee_id', '==', employee_id)\
            .where('date', '==', date_str)\
            .where('jenis', '==', jenis_absen)\
            .get()

        if len(existing) > 0:
            return jsonify({"error": f"Sudah absen {jenis_absen} hari ini!"}), 400

        new_attendance = {
            'employee_id': employee_id,
            'employee_name': employee_name,
            'date': date_str,
            'clock_in': time_str,
            'clock_out': '-',
            'status': 'Bekerja',
            'jenis': jenis_absen,
            'timestamp': datetime.now() 
        }

        db.collection(COLLECTION_NAME).add(new_attendance)
        return jsonify({"message": "Berhasil!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500