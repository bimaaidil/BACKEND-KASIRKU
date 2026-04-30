from flask import Blueprint, request, jsonify
import requests
from firebase_config import db
from datetime import datetime, timedelta
import random

# Import otak AI
from ai_core.prediction_service import predict_sales

prediksi_bp = Blueprint('prediksi', __name__)

# --- API CUACA (OPEN-METEO) ---
def get_real_weather():
    try:
        # Koordinat Pekanbaru
        lat, lon = 0.5071, 101.4478 
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,weathercode&timezone=Asia%2FBangkok"
        
        response = requests.get(url).json()
        
        temp_max = response['daily']['temperature_2m_max'][1]
        weather_code = response['daily']['weathercode'][1]
        
        condition = "Cerah"
        insight = "Cuaca besok mendukung penjualan!"
        factor = 0.9

        if weather_code >= 51: 
            condition = "Hujan"
            insight = "Waspada hujan! Stok mungkin aman."
            factor = 0.3 
        elif weather_code <= 3: 
            condition = "Cerah Berawan"
            insight = "Suhu hangat, stok buah aman."
            factor = 0.8
            
        return { "temp": temp_max, "condition": condition, "insight": insight, "factor": factor }
    except Exception as e:
        print(f"Gagal ambil cuaca: {e}")
        return {"temp": 30, "condition": "Cerah", "insight": "Koneksi gangguan, asumsi cerah.", "factor": 0.8}

@prediksi_bp.route('', methods=['GET'])
def get_prediction():
    try:
        # 1. AMBIL CUACA BESOK
        weather = get_real_weather()

        # 2. AMBIL DATA BAHAN BAKU
        products_ref = db.collection('products').stream()
        recommendations = []
        
        for doc in products_ref:
            prod = doc.to_dict()
            
            # --- [PERBAIKAN UTAMA DISINI] ---
            # Sesuaikan dengan nama kolom di Firestore Anda (image_cc443e.jpg)
            
            # 1. Ambil Nama (Cari 'nama' dulu, baru 'name')
            prod_name = prod.get('nama') or prod.get('name') or "Produk Tanpa Nama"
            
            # 2. Ambil Stok (Cari 'stok' dulu, baru 'stock')
            # Konversi ke int agar aman jika di db tertulis string "15"
            try:
                raw_stock = prod.get('stok') or prod.get('stock') or 0
                current_stock = int(raw_stock)
            except:
                current_stock = 0

            unit = prod.get('unit', 'kg')
            
            # --- DUMMY DATA HISTORY (UNTUK DEMO) ---
            dummy_history = [
                random.randint(5, 15), 
                random.randint(5, 15), 
                random.randint(8, 20), 
                random.randint(8, 20), 
                random.randint(10, 25) 
            ]
            
            # PANGGIL OTAK AI
            predicted_qty = predict_sales(dummy_history, weather['factor'])
            
            recommendations.append({
                "id": doc.id,
                "name": prod_name,      # Kirim ke frontend sebagai 'name'
                "currentStock": current_stock,
                "predicted": predicted_qty,
                "unit": unit
            })

        # 3. DATA GRAFIK
        chart_data = [
            {"date": "H-4", "penjualan": random.randint(10, 20)},
            {"date": "H-3", "penjualan": random.randint(15, 25)},
            {"date": "H-2", "penjualan": random.randint(12, 22)},
            {"date": "Kemarin", "penjualan": random.randint(18, 28)},
            {"date": "Besok (AI)", "penjualan": sum(d['predicted'] for d in recommendations) // (len(recommendations) or 1) + 5}
        ]

        return jsonify({
            "weather": weather,
            "chart": chart_data,
            "recommendations": recommendations
        }), 200

    except Exception as e:
        print(f"Error Backend: {e}")
        return jsonify({"error": str(e)}), 500