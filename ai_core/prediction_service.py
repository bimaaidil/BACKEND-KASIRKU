import numpy as np
import pandas as pd
import tensorflow as tf
import joblib
import os

# Konfigurasi Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'model_bilstm.h5')
SCALER_PATH = os.path.join(BASE_DIR, 'scaler.pkl')

model = None
scaler = None

def load_ai_model():
    global model, scaler
    try:
        if os.path.exists(MODEL_PATH):
            model = tf.keras.models.load_model(MODEL_PATH)
            print("✅ Model Bi-LSTM Berhasil Dimuat!")
        if os.path.exists(SCALER_PATH):
            scaler = joblib.load(SCALER_PATH)
            print("✅ Scaler Berhasil Dimuat!")
    except Exception as e:
        print(f"❌ Error loading model: {e}")

load_ai_model()

def predict_sales(weather_factor=0.5):
    try:
        # 1. Konfigurasi Stok Awal Minimum (Safety Stock)
        min_stock_config = {
            "Apel": {"qty": 2, "unit": "kg", "ratio": 0.02},
            "Belimbing": {"qty": 2, "unit": "kg", "ratio": 0.02},
            "Jagung": {"qty": 2, "unit": "kg", "ratio": 0.02},
            "Jeruk": {"qty": 7, "unit": "kg", "ratio": 0.05},
            "Jambu": {"qty": 2, "unit": "kg", "ratio": 0.02},
            "Mangga": {"qty": 10, "unit": "kg", "ratio": 0.06},
            "Melon": {"qty": 2, "unit": "buah", "ratio": 0.02},
            "Naga": {"qty": 5, "unit": "kg", "ratio": 0.04},
            "Nenas": {"qty": 2, "unit": "buah", "ratio": 0.02},
            "Pokat": {"qty": 30, "unit": "kg", "ratio": 0.15},
            "Semangka": {"qty": 2, "unit": "buah", "ratio": 0.02},
            "Sirsak": {"qty": 5, "unit": "kg", "ratio": 0.04},
            "Terong Belanda": {"qty": 3, "unit": "kg", "ratio": 0.03},
            "Timun": {"qty": 2, "unit": "kg", "ratio": 0.02}
        }

# 2. Prediksi Tren via Bi-LSTM
        csv_path = os.path.join(BASE_DIR, '../dataset/dataset_penjualan.csv')
        total_cups_predicted = 150 

        if os.path.exists(csv_path):
            # Membaca CSV dengan separator titik koma (sesuai dataset Anda)
            df = pd.read_csv(csv_path, sep=';')
            df['Tanggal'] = pd.to_datetime(df['Tanggal'], dayfirst=True)
            
            if not df.empty:
                # Ambil 7 hari terakhir
                last_7_days = df.tail(7).copy()
                
                # Buat fitur weekend (Sama seperti saat training)
                last_7_days['Hari'] = last_7_days['Tanggal'].dt.weekday
                last_7_days['is_weekend'] = last_7_days['Hari'].map(lambda x: 1 if x >= 5 else 0)
                
                # Menyiapkan Input (Sales & Weekend)
                sales_data = last_7_days['Total_Produk_Terjual'].values.reshape(-1, 1)
                scaled_sales = scaler.transform(sales_data)
                scaled_weekend = last_7_days['is_weekend'].values.reshape(-1, 1)
                
                # Gabungkan menjadi 2 kolom (Sangat Penting!)
                X_input = np.hstack((scaled_sales, scaled_weekend))
                X_input = X_input.reshape(1, 7, 2) # 1 sampel, 7 hari, 2 fitur
                
                # Jalankan Prediksi
                pred_scaled = model.predict(X_input, verbose=0)
                total_cups_predicted = scaler.inverse_transform(pred_scaled)[0][0]

        # 3. Pengaruh Cuaca
        weather_multiplier = 1.0
        is_raining = weather_factor <= 0.4
        if weather_factor >= 0.8: 
            weather_multiplier = 1.1
        elif is_raining: 
            weather_multiplier = 0.7

        # 4. Gabungkan Logika (Adaptif & Fixed untuk Buah Satuan)
        results = []
        buah_tetap = ['Nenas', 'Melon', 'Semangka', 'Nanas']

        for name, config in min_stock_config.items():
            ai_demand = total_cups_predicted * config['ratio'] * weather_multiplier
            
            # --- LOGIKA KHUSUS NENAS, MELON, SEMANGKA ---
            if any(b in name for b in buah_tetap):
                # Target selalu 2 buah, tidak peduli hujan atau prediksi AI
                final_target = 2 
            
            # --- LOGIKA UNTUK BUAH LAIN ---
            elif is_raining:
                # Hujan: Target boleh turun di bawah stok awal (Efisiensi)
                final_target = max(1, ai_demand)
            else:
                # Normal: Gunakan batas aman minimal
                final_target = max(config['qty'], ai_demand)

            results.append({
                "name": name,
                "predicted": int(np.ceil(final_target)),
                "unit": config['unit']
            })

        return results

    except Exception as e:
        print(f"❌ Error in prediction_service: {e}")
        return []