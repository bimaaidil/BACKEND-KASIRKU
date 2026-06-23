# routes/transaksi.py
from flask import Blueprint, request, jsonify
from firebase_config import db
from datetime import datetime
import pandas as pd
import os
import io

# --- IMPORT GOOGLE DRIVE API LIBRARIES ---
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

transaksi_bp = Blueprint('transaksi', __name__)
COLLECTION_NAME = 'transactions'

# SCOPES & CONFIGURATION GOOGLE DRIVE
SCOPES = ['https://www.googleapis.com/auth/drive']
# GANTI string di bawah ini dengan File ID dari Google Drive kamu yang dicatat di Tahap 1
GOOGLE_DRIVE_FILE_ID = '1VPHMSeWUrd3uFs1Q0TmnLZyjBWA6_Jo7'

# Path absolut ke file kunci akses JSON di root folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')

def get_drive_service():
    """Fungsi helper untuk membuat koneksi terotentikasi ke Google Drive API"""
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(f"File kredensial tidak ditemukan di: {CREDENTIALS_PATH}")
    
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def update_sales_csv(items, total_terjual):
    try:
        print("🔗 Menghubungkan ke Google Drive API...")
        service = get_drive_service()
        
        # 1. UNDUH FILE CSV DARI GOOGLE DRIVE KE MEMORI RAM SERVER
        request_download = service.files().get_media(fileId=GOOGLE_DRIVE_FILE_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request_download)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"📥 Mengunduh CSV dari Drive... {int(status.progress() * 100)}%")
            
        fh.seek(0)
        
        # 2. BACA DATASET MENGGUNAKAN PANDAS DARI STRUKTUR BYTES MEMORI
        df_csv = pd.read_csv(fh, sep=';')
        df_csv['Tanggal'] = df_csv['Tanggal'].astype(str)
        
        # Format tanggal sesuai dataset (DD/MM/YYYY)
        today_str = datetime.now().strftime('%d/%m/%Y')
        
        # 3. CARI ATAU BUAT BARIS UNTUK HARI INI
        if today_str in df_csv['Tanggal'].values:
            idx = df_csv.index[df_csv['Tanggal'] == today_str][0]
            df_csv.at[idx, 'Total_Produk_Terjual'] = int(df_csv.at[idx, 'Total_Produk_Terjual']) + total_terjual
            print(f"📊 Mengupdate baris {today_str} di memori: +{total_terjual} unit")
        else:
            new_row = {col: 0 for col in df_csv.columns}
            new_row['Tanggal'] = today_str
            new_row['Total_Produk_Terjual'] = total_terjual
            new_row['Status_Toko'] = 1
            
            df_csv = pd.concat([df_csv, pd.DataFrame([new_row])], ignore_index=True)
            idx = df_csv.index[df_csv['Tanggal'] == today_str][0]
            print(f"🆕 Membuat baris baru tanggal {today_str} di memori")

        # 4. LOGIKA UPDATE KOLOM BUAH SPESIFIK (ADAPTIF DWIBAHASA)
        for item in items:
            nama_produk = item.get('nama') or item.get('name') or item.get('product')
            qty_produk = int(item.get('qty') or item.get('quantity') or 0)
            
            if not nama_produk:
                continue

            if nama_produk in df_csv.columns:
                current_val = df_csv.at[idx, nama_produk]
                df_csv.at[idx, nama_produk] = int(current_val) + qty_produk
                print(f"🍊 Kolom [{nama_produk}] diperbarui: +{qty_produk}")
            else:
                # Fallback pencarian huruf kecil/besar jika ejaan mirip
                matched_column = None
                for col in df_csv.columns:
                    if col.lower() == nama_produk.lower():
                        matched_column = col
                        break
                
                if matched_column:
                    current_val = df_csv.at[idx, matched_column]
                    df_csv.at[idx, matched_column] = int(current_val) + qty_produk
                    print(f"🍊 Kolom alternatif [{matched_column}] diperbarui: +{qty_produk}")
                else:
                    print(f"⚠️ Kolom untuk produk [{nama_produk}] tidak ditemukan di CSV Google Drive.")

        # 5. UBAH DATAFRAME KEMBALI MENJADI STRING STREAM BYTES CSV
        output_stream = io.StringIO()
        df_csv.to_csv(output_stream, sep=';', index=False)
        output_stream.seek(0)
        
        # Konversi String ke Bytes murni yang siap dikirim lewat protokol HTTP
        media_body = MediaIoBaseUpload(
            io.BytesIO(output_stream.getvalue().encode('utf-8')), 
            mimetype='text/csv', 
            resumable=True
        )
        
        # 6. UNGGAH KEMBALI DAN OVERWRITE FILE TERSEBUT DI GOOGLE DRIVE CLOUD
        updated_file = service.files().update(
            fileId=GOOGLE_DRIVE_FILE_ID,
            media_body=media_body
        ).execute()
        
        print(f"✅ [AI-Cloud-Sync] Dataset fisik di Google Drive SUKSES di-update! File ID: {updated_file.get('id')}")
        
    except Exception as e:
        print(f"❌ [AI-Cloud-Sync] Gagal sinkronisasi ke Google Drive: {e}")


# 1. SIMPAN TRANSAKSI (POST)
@transaksi_bp.route('', methods=['POST'])
def add_transaction():
    print("🚀 Permintaan Transaksi Diterima!") 
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Data kosong"}), 400
            
        print(f"📦 Data yang masuk: {data}") 

        data['timestamp'] = datetime.now()
        data['date'] = datetime.now().strftime("%Y-%m-%d") 
        
        # A. Simpan ke Firestore (Data Riwayat Terpusat)
        db.collection(COLLECTION_NAME).add(data)
        
        # B. INTEGRASI AI GOOGLE DRIVE SYNC
        items = data.get('items', [])
        
        total_qty = 0
        for item in items:
            val = item.get('qty') or item.get('quantity') or 0
            total_qty += int(val)
        
        print(f"🔢 Total Item Terdeteksi: {total_qty}")

        if total_qty > 0:
            update_sales_csv(items, total_qty)
        else:
            print("⚠️ Tidak ada qty produk untuk diupdate.")
        
        return jsonify({"message": "Transaksi berhasil disimpan dan Google Drive CSV Updated!"}), 201
        
    except Exception as e:
        print(f"Error Transaksi: {e}")
        return jsonify({"error": str(e)}), 500

# 2. AMBIL RIWAYAT TRANSAKSI (GET)
@transaksi_bp.route('', methods=['GET'])
def get_transactions():
    try:
        transaksi_ref = db.collection(COLLECTION_NAME)
        
        try:
            docs = transaksi_ref.order_by('timestamp', direction='DESCENDING').stream()
        except Exception:
            docs = transaksi_ref.stream()
            
        result = []
        for doc in docs:
            t = doc.to_dict()
            t['id'] = doc.id
            if 'timestamp' in t and t['timestamp'] is not None:
                t['timestamp'] = str(t['timestamp'])
            result.append(t)
            
        if 'timestamp' in result[0] if result else False:
            result = sorted(result, key=lambda x: x.get('timestamp', ''), reverse=True)
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500