import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
import joblib
import os

# --- KONFIGURASI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'model_bilstm.h5')
SCALER_PATH = os.path.join(BASE_DIR, 'scaler.pkl')

# Global variable agar model diload sekali saja
model = None
scaler = None

def load_ai_model():
    global model, scaler
    try:
        if os.path.exists(MODEL_PATH):
            model = tf.keras.models.load_model(MODEL_PATH)
            print("✅ Model Bi-LSTM Berhasil Dimuat!")
        else:
            print("⚠️ File model_bilstm.h5 tidak ditemukan. Menggunakan Mode Simulasi.")

        if os.path.exists(SCALER_PATH):
            scaler = joblib.load(SCALER_PATH)
        else:
            print("⚠️ Scaler tidak ditemukan. Menggunakan Mode Manual.")
            
    except Exception as e:
        print(f"❌ Gagal memuat AI: {e}")

# Panggil fungsi load saat server nyala
load_ai_model()

def predict_sales(history_data, weather_factor):
    """
    Fungsi Utama Prediksi:
    - history_data: List penjualan 7 hari terakhir [10, 12, 15, ...]
    - weather_factor: Angka faktor cuaca (0 - 1)
    """
    try:
        # Jika model ada, kita gunakan Bi-LSTM beneneran
        if model and scaler:
            input_data = np.array(history_data).reshape(-1, 1)
            scaled_data = scaler.transform(input_data)
            
            # Ambil 5 data terakhir sebagai input
            X_input = np.array([scaled_data[-5:]]) 
            X_input = np.reshape(X_input, (X_input.shape[0], X_input.shape[1], 1))
            
            # PREDIKSI
            prediction_scaled = model.predict(X_input, verbose=0)
            
            # Denormalisasi
            prediction_real = scaler.inverse_transform(prediction_scaled)
            final_result = float(prediction_real[0][0])
            
            # Koreksi Cuaca
            if weather_factor > 0.8: final_result *= 1.2 
            elif weather_factor < 0.3: final_result *= 0.8 
                
            return int(round(final_result))

        else:
            # --- FALLBACK / SIMULASI CERDAS ---
            # Jika model belum ada, gunakan logika rata-rata tertimbang
            avg = np.average(history_data, weights=[0.1, 0.1, 0.2, 0.2, 0.4])
            prediction = avg * (1 + (weather_factor - 0.5)) 
            return int(max(0, round(prediction)))

    except Exception as e:
        print(f"Error saat prediksi: {e}")
        return 0