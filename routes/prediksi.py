# backend/routes/prediksi.py
from flask import Blueprint, request, jsonify
import requests
from firebase_config import db
import random
from datetime import datetime

# Import fungsi utama AI
from ai_core.prediction_service import predict_sales

# Tetapkan blueprint name tetap 'prediksi'
prediksi_bp = Blueprint('prediksi', __name__)

def get_real_weather(weather_index=1):
    """
    Mengambil data cuaca berdasarkan indeks hari.
    weather_index 0 = Hari Ini
    weather_index 1 = Besok
    """
    try:
        # Koordinat Pekanbaru (Lokasi Varisha Jus)
        lat, lon = 0.5071, 101.4478 
        
        # Menambahkan hourly=relative_humidity_2m di URL API Open-Meteo
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,weathercode&hourly=relative_humidity_2m&timezone=Asia%2FBangkok"
        res = requests.get(url).json()
        
        temp = res['daily']['temperature_2m_max'][weather_index]
        code = res['daily']['weathercode'][weather_index]
        
        # Mengambil data kelembapan (humidity) pada jam 12:00 siang di hari target
        hour_index = (weather_index * 24) + 12
        humidity = res['hourly']['relative_humidity_2m'][hour_index]
        
        # Logika interpretasi kode cuaca
        cond, insight, factor = "Cerah", "Cuaca bagus untuk jualan!", 0.9
        if code >= 51:
            cond, insight, factor = "Hujan", "Waspada hujan! Stok dikurangi agar efisien.", 0.3
        elif code <= 3:
            cond, insight, factor = "Cerah Berawan", "Suhu stabil, stok buah aman.", 0.8
            
        return {
            "temp": temp, 
            "condition": cond, 
            "humidity": humidity, 
            "insight": insight, 
            "factor": factor
        }
    except Exception as e:
        print(f"❌ Weather API Error: {e}")
        # Fallback data jika API Open-Meteo mengalami gangguan/limit
        return {"temp": 30, "condition": "Cerah", "humidity": 75, "insight": "Mode Offline Aktif.", "factor": 0.8}

# PERBAIKAN RUTING: Ubah '' menjadi '/prediksi' agar cocok dengan axios.get di frontend kamu!
@prediksi_bp.route('/prediksi', methods=['GET'])
def get_prediction():
    try:
        # 1. LOGIKA WAKTU OPERASIONAL (Belanja Subuh vs Prediksi Besok)
        now = datetime.now()
        current_hour = now.hour
        
        if current_hour < 6:
            target_label = "Hari Ini"
            w_index = 0 
            display_date = now.strftime("%A, %d %B %Y")
        else:
            target_label = "Besok"
            w_index = 1
            display_date = "Besok" 

        # 2. Ambil data cuaca sesuai indeks waktu
        weather = get_real_weather(w_index)

        # 3. Ambil hasil prediksi dari AI Service (Bi-LSTM + Logic Hybrid)
        ai_data = predict_sales(weather['factor'])

        # 4. Ambil stok aktual dari Firestore
        prods_ref = db.collection('products').stream()
        db_items = []
        for d in prods_ref:
            p = d.to_dict()
            name_db = (p.get('nama') or p.get('name') or "").strip().lower()
            db_items.append({
                "id": d.id, 
                "name": name_db, 
                "stok": float(p.get('stok') or 0)
            })

        # 5. Sinkronisasi Data (Matching nama produk AI dengan Database)
        final_recommendations = []
        for item in ai_data:
            ai_name_lower = item['name'].lower().strip()
            
            # Cari produk yang cocok di Firestore (fuzzy match sederhana)
            match = next((x for x in db_items if ai_name_lower in x['name'] or x['name'] in ai_name_lower), None)
            
            if match:
                final_recommendations.append({
                    "id": match['id'],
                    "name": item['name'],
                    "currentStock": match['stok'],
                    "predicted": item['predicted'],
                    "unit": item['unit']
                })

        # 6. Data untuk Visualisasi Grafik (Dummy untuk demo tren porsi)
        chart_data = [
            {"date": "H-4", "penjualan": random.randint(110, 140)},
            {"date": "H-3", "penjualan": random.randint(120, 150)},
            {"date": "H-2", "penjualan": random.randint(115, 145)},
            {"date": "Kemarin", "penjualan": random.randint(160, 190)},
            {"date": "Target AI", "penjualan": 212}
        ]

        return jsonify({
            "status": "success",
            "target_info": {
                "label": target_label,
                "date": display_date
            },
            "weather": weather,
            "chart": chart_data,
            "recommendations": final_recommendations
        }), 200

    except Exception as e:
        print(f"❌ Error pada Route Prediksi: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500