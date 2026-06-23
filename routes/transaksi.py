# routes/transaksi.py
from flask import Blueprint, request, jsonify
from firebase_config import db
from datetime import datetime
import pandas as pd
import os

# Nama blueprint disesuaikan dengan yang di-import di app.py
transaksi_bp = Blueprint('transaksi', __name__)
COLLECTION_NAME = 'transactions'

#  FUNGSI HELPER: UPDATE DATASET CSV UNTUK AI 
def update_sales_csv(items, total_terjual):
    try:
        # Menentukan lokasi file dataset_penjualan.csv secara absolut
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, 'dataset', 'dataset_penjualan.csv')
        
        # Format tanggal sesuai dataset (DD/MM/YYYY)
        today_str = datetime.now().strftime('%d/%m/%Y')
        
        # Cek keberadaan file
        if not os.path.exists(csv_path):
            print(f"❌ File tidak ditemukan di: {csv_path}")
            return

        # Baca dataset
        df_csv = pd.read_csv(csv_path, sep=';')
        
        # Pastikan kolom Tanggal bertipe string untuk pencocokan
        df_csv['Tanggal'] = df_csv['Tanggal'].astype(str)

        # 1. Cari atau buat baris untuk hari ini
        if today_str in df_csv['Tanggal'].values:
            idx = df_csv.index[df_csv['Tanggal'] == today_str][0]
            # Update total terjual secara keseluruhan
            df_csv.at[idx, 'Total_Produk_Terjual'] = int(df_csv.at[idx, 'Total_Produk_Terjual']) + total_terjual
            print(f"📊 Mengupdate baris {today_str}: +{total_terjual} unit total")
        else:
            # Buat baris baru jika hari baru
            new_row = {col: 0 for col in df_csv.columns}
            new_row['Tanggal'] = today_str
            new_row['Total_Produk_Terjual'] = total_terjual
            new_row['Status_Toko'] = 1
            
            df_csv = pd.concat([df_csv, pd.DataFrame([new_row])], ignore_index=True)
            idx = df_csv.index[df_csv['Tanggal'] == today_str][0]
            print(f"🆕 Membuat baris baru untuk tanggal {today_str}")

        # 2. LOGIKA UPDATE KOLOM BUAH SPESIFIK
        for item in items:
            # Ambil nama produk dan qty (mendukung kunci 'qty' atau 'quantity')
            nama_produk = item.get('name')
            qty_produk = int(item.get('qty') or item.get('quantity') or 0)
            
            # Cek apakah nama produk ada dalam kolom CSV (case-sensitive)
            if nama_produk in df_csv.columns:
                current_val = df_csv.at[idx, nama_produk]
                df_csv.at[idx, nama_produk] = int(current_val) + qty_produk
                print(f"🍊 Kolom [{nama_produk}] berhasil diupdate: +{qty_produk}")
            else:
                print(f"⚠️ Kolom untuk produk [{nama_produk}] tidak ditemukan di CSV. Pastikan ejaan sama.")

        # 3. Simpan kembali ke file CSV
        df_csv.to_csv(csv_path, sep=';', index=False)
        print(f"✅ [AI-Sync] Dataset fisik berhasil diupdate sepenuhnya di: {csv_path}")
        
    except Exception as e:
        print(f"❌ [AI-Sync] Gagal update CSV: {e}")


# 1. SIMPAN TRANSAKSI (POST)
@transaksi_bp.route('', methods=['POST'])
def add_transaction():
    print("🚀 Permintaan Transaksi Diterima!") 
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Data kosong"}), 400
            
        print(f"📦 Data yang masuk: {data}") 

        # Tambahkan timestamp server
        data['timestamp'] = datetime.now()
        data['date'] = datetime.now().strftime("%Y-%m-%d") 
        
        # A. Simpan ke Firestore (Data Riwayat)
        db.collection(COLLECTION_NAME).add(data)
        
        # B. INTEGRASI AI
        items = data.get('items', [])
        
        # Hitung total quantity
        total_qty = 0
        for item in items:
            val = item.get('qty') or item.get('quantity') or 0
            total_qty += int(val)
        
        print(f"🔢 Total Item Terdeteksi: {total_qty}")

        if total_qty > 0:
            # Panggil fungsi helper dengan menyertakan daftar items
            update_sales_csv(items, total_qty)
        else:
            print("⚠️ Tidak ada qty produk untuk diupdate ke CSV.")
        
        return jsonify({"message": "Transaksi berhasil disimpan dan AI Updated!"}), 201
        
    except Exception as e:
        print(f"Error Transaksi: {e}")
        return jsonify({"error": str(e)}), 500

# 2. AMBIL RIWAYAT TRANSAKSI (GET)
@transaksi_bp.route('', methods=['GET'])
def get_transactions():
    try:
        transaksi_ref = db.collection(COLLECTION_NAME)
        
        # Menggunakan perlindungan try-except query untuk mengantisipasi jika index Firestore belum dibuat
        try:
            docs = transaksi_ref.order_by('timestamp', direction='DESCENDING').stream()
        except Exception:
            # Fallback otomatis jika order_by timestamp melempar error di cloud
            docs = transaksi_ref.stream()
            
        result = []
        for doc in docs:
            t = doc.to_dict()
            t['id'] = doc.id
            
            # Amankan konversi tipe data objek datetime menjadi string standard ISO agar tidak eror di React
            if 'timestamp' in t and t['timestamp'] is not None:
                t['timestamp'] = str(t['timestamp'])
                
            result.append(t)
            
        # Jika menggunakan fallback stream biasa, lakukan penyortiran array di tingkat Python demi kestabilan data
        if 'timestamp' in result[0] if result else False:
            result = sorted(result, key=lambda x: x.get('timestamp', ''), reverse=True)
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500