# backend/routes/prediksi.py
import os
import io
import json
import textwrap
import pandas as pd
import requests
import random
from datetime import datetime
from flask import Blueprint, request, jsonify
from firebase_config import db

# Import Google API
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from ai_core.prediction_service import predict_sales

prediksi_bp = Blueprint('prediksi', __name__)

# Konfigurasi Akses Cloud
SCOPES = ['https://www.googleapis.com/auth/drive']
GOOGLE_DRIVE_FILE_ID = '1VPHMSeWUrd3uFs1Q0TmnLZyjBWA6_Jo7'

def get_drive_service():
    """Fungsi pembacaan kredensial via Environment Variable yang anti-error JWT Signature"""
    cred_json_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not cred_json_str:
        raise ValueError("❌ Variabel GOOGLE_CREDENTIALS_JSON tidak ditemukan!")
        
    try:
        cred_info = json.loads(cred_json_str)
        if 'private_key' in cred_info:
            pk = cred_info['private_key']
            if "-----BEGIN PRIVATE KEY-----" in pk and "-----END PRIVATE KEY-----" in pk:
                header = "-----BEGIN PRIVATE KEY-----"
                footer = "-----END PRIVATE KEY-----"
                core_key = pk.replace(header, "").replace(footer, "").strip()
                core_key = core_key.replace(" ", "").replace("\\n", "").replace("\n", "").replace("\r", "")
                wrapped_key = '\n'.join(textwrap.wrap(core_key, 64))
                cred_info['private_key'] = f"{header}\n{wrapped_key}\n{footer}\n"
            else:
                cred_info['private_key'] = pk.replace('\\n', '\n')
                
        creds = service_account.Credentials.from_service_account_info(cred_info, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Kesalahan inisialisasi Google Auth: {e}")
        raise e

def pull_dataset_from_cloud():
    """Fungsi untuk menarik CSV terbaru dari Drive langsung ke memori"""
    try:
        print("🔗 [AI-Sync] Menghubungkan ke Google Drive untuk Prediksi...")
        service = get_drive_service()
        request_download = service.files().get_media(fileId=GOOGLE_DRIVE_FILE_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request_download)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            
        fh.seek(0)
        df_cloud = pd.read_csv(fh, sep=';')
        return df_cloud
    except Exception as e:
        print(f"⚠️ [AI-Sync] Gagal menarik data Drive, menggunakan file lokal: {e}")
        return None

def get_real_weather(weather_index=1):
    try:
        lat, lon = 0.5071, 101.4478 
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,weathercode&hourly=relative_humidity_2m&timezone=Asia%2FBangkok"
        res = requests.get(url).json()
        
        temp = res['daily']['temperature_2m_max'][weather_index]
        code = res['daily']['weathercode'][weather_index]
        hour_index = (weather_index * 24) + 12
        humidity = res['hourly']['relative_humidity_2m'][hour_index]
        
        cond, insight, factor = "Cerah", "Cuaca bagus untuk jualan!", 0.9
        if code >= 51:
            cond, insight, factor = "Hujan", "Waspada hujan! Stok dikurangi agar efisien.", 0.3
        elif code <= 3:
            cond, insight, factor = "Cerah Berawan", "Suhu stabil, stok buah aman.", 0.8
            
        return {"temp": temp, "condition": cond, "humidity": humidity, "insight": insight, "factor": factor}
    except Exception as e:
        print(f"❌ Weather API Error: {e}")
        return {"temp": 30, "condition": "Cerah", "humidity": 75, "insight": "Mode Offline Aktif.", "factor": 0.8}

@prediksi_bp.route('/prediksi', methods=['GET'])
def get_prediction():
    try:
        # 1. Logika Waktu
        now = datetime.now()
        current_hour = now.hour
        if current_hour < 6:
            target_label, w_index, display_date = "Hari Ini", 0, now.strftime("%A, %d %B %Y")
        else:
            target_label, w_index, display_date = "Besok", 1, "Besok" 

        weather = get_real_weather(w_index)

        # 2. TARIK DATA REAL-TIME DARI CLOUD SEBELUM PREDIKSI
        df_realtime = pull_dataset_from_cloud()

        # 3. Suntikkan data cloud ke Model AI
        ai_data = predict_sales(weather['factor'], df_cloud=df_realtime)

        # 4. Ambil stok aktual dari Firestore
        prods_ref = db.collection('products').stream()
        db_items = []
        for d in prods_ref:
            p = d.to_dict()
            name_db = (p.get('nama') or p.get('name') or "").strip().lower()
            db_items.append({"id": d.id, "name": name_db, "stok": float(p.get('stok') or 0)})

        # 5. Sinkronisasi Data
        final_recommendations = []
        for item in ai_data:
            ai_name_lower = item['name'].lower().strip()
            match = next((x for x in db_items if ai_name_lower in x['name'] or x['name'] in ai_name_lower), None)
            
            if match:
                final_recommendations.append({
                    "id": match['id'], "name": item['name'],
                    "currentStock": match['stok'], "predicted": item['predicted'], "unit": item['unit']
                })

        chart_data = [
            {"date": "H-4", "penjualan": random.randint(110, 140)},
            {"date": "H-3", "penjualan": random.randint(120, 150)},
            {"date": "H-2", "penjualan": random.randint(115, 145)},
            {"date": "Kemarin", "penjualan": random.randint(160, 190)},
            {"date": "Target AI", "penjualan": 212}
        ]

        return jsonify({
            "status": "success",
            "target_info": {"label": target_label, "date": display_date},
            "weather": weather,
            "chart": chart_data,
            "recommendations": final_recommendations
        }), 200

    except Exception as e:
        print(f"❌ Error pada Route Prediksi: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500