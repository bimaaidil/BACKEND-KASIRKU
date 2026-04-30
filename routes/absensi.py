from flask import Blueprint, request, jsonify
from firebase_config import db
from datetime import datetime

absensi_bp = Blueprint('absensi', __name__)
COLLECTION_NAME = 'attendance'

# --- 1. AMBIL DATA (GET) ---
@absensi_bp.route('', methods=['GET'])
def get_absensi():
    try:
        docs = db.collection(COLLECTION_NAME).order_by('timestamp', direction='DESCENDING').stream()
        result = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            if 'timestamp' in data: data['timestamp'] = str(data['timestamp'])
            result.append(data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 2. ABSEN MASUK (BISA REGULER / LEMBUR) ---
@absensi_bp.route('/clock-in', methods=['POST'])
def clock_in():
    try:
        data = request.json
        employee_id = data.get('employee_id')
        employee_name = data.get('employee_name')
        # Parameter baru: jenis_absen (Default 'Reguler' jika tidak ada)
        jenis_absen = data.get('jenis_absen', 'Reguler') 
        
        if not employee_id:
            return jsonify({"error": "Pilih karyawan dulu!"}), 400

        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M:%S')

        # CEK DUPLIKAT SPESIFIK:
        # Kita cari apakah sudah ada absen dengan TANGGAL sama DAN JENIS sama
        existing = db.collection(COLLECTION_NAME)\
            .where('employee_id', '==', employee_id)\
            .where('date', '==', date_str)\
            .where('jenis', '==', jenis_absen)\
            .get()

        if len(existing) > 0:
            return jsonify({"error": f"Anda sudah absen {jenis_absen} hari ini!"}), 400

        new_attendance = {
            'employee_id': employee_id,
            'employee_name': employee_name,
            'date': date_str,
            'clock_in': time_str,
            'clock_out': '-',
            'status': 'Bekerja',     # Status awal
            'jenis': jenis_absen,    # 'Reguler' atau 'Lembur'
            'timestamp': datetime.now() 
        }

        db.collection(COLLECTION_NAME).add(new_attendance)
        return jsonify({"message": f"Absen {jenis_absen} Berhasil!"}), 201
    except Exception as e:
        print(f"Error Clock In: {e}")
        return jsonify({"error": str(e)}), 500

# --- 3. ABSEN PULANG (OTOMATIS CARI YG BELUM SELESAI) ---
@absensi_bp.route('/clock-out', methods=['POST'])
def clock_out():
    try:
        data = request.json
        employee_id = data.get('employee_id')
        
        if not employee_id:
             return jsonify({"error": "ID Karyawan tidak valid"}), 400

        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M:%S')

        # Cari data hari ini milik karyawan ini yang clock_out nya masih "-"
        docs = db.collection(COLLECTION_NAME)\
            .where('employee_id', '==', employee_id)\
            .where('date', '==', date_str)\
            .where('clock_out', '==', '-')\
            .get()
        
        if not docs:
            return jsonify({"error": "Tidak ada sesi aktif untuk diakhiri."}), 404

        # Ambil dokumen pertama yg ditemukan (entah itu Reguler atau Lembur)
        doc_ref = docs[0].reference
        doc_ref.update({
            'clock_out': time_str,
            'status': 'Selesai'
        })
        
        return jsonify({"message": "Hati-hati di jalan!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 4. REKAP BULANAN (UPDATE AGAR LEMBUR TIDAK DIHITUNG 2 HARI) ---
@absensi_bp.route('/rekap-bulanan', methods=['GET'])
def get_rekap_bulanan():
    try:
        bulan_dicari = request.args.get('bulan')
        if not bulan_dicari: return jsonify({"error": "Pilih bulan!"}), 400

        docs = db.collection(COLLECTION_NAME).stream()
        laporan = {}

        for doc in docs:
            data = doc.to_dict()
            tanggal_absen = data.get('date', '') 
            jenis = data.get('jenis', 'Reguler') # Ambil jenis

            if tanggal_absen.startswith(bulan_dicari):
                emp_id = data.get('employee_id')
                emp_name = data.get('employee_name')

                if emp_id not in laporan:
                    laporan[emp_id] = { "nama": emp_name, "total_hadir": 0, "lembur_count": 0, "dates": set() }
                
                # Hitung Kehadiran (Gunakan Set agar tanggal sama tidak dihitung 2x)
                if jenis == 'Reguler':
                    laporan[emp_id]["dates"].add(tanggal_absen)
                
                # Hitung Berapa kali dia lembur
                if jenis == 'Lembur':
                    laporan[emp_id]["lembur_count"] += 1

        hasil_akhir = []
        for uid, info in laporan.items():
            hasil_akhir.append({
                "nama": info['nama'],
                "total_hadir": len(info['dates']), # Total hari unik
                "total_lembur": info['lembur_count'] # Total kali lembur
            })
        
        hasil_akhir = sorted(hasil_akhir, key=lambda x: x['nama'])
        return jsonify(hasil_akhir), 200

    except Exception as e:
        print(f"Error Rekap: {e}")
        return jsonify({"error": str(e)}), 500