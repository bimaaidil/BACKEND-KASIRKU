import numpy as np
import pandas as pd
import joblib
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'model_bilstm.h5')
SCALER_PATH = os.path.join(BASE_DIR, 'scaler.pkl')

model = None
scaler = None

def load_ai_model():
    global model, scaler
    try:
        try:
            import tensorflow as tf
            if os.path.exists(MODEL_PATH):
                model = tf.keras.models.load_model(MODEL_PATH)
                print("✅ Model Bi-LSTM Berhasil Dimuat!")
        except ImportError:
            print("⚠️ TensorFlow tidak ditemukan di cloud. Mengaktifkan Fallback Mode.")

        if os.path.exists(SCALER_PATH):
            scaler = joblib.load(SCALER_PATH)
            print("✅ Scaler Berhasil Dimuat!")
    except Exception as e:
        print(f"❌ Error loading model: {e}")

load_ai_model()

# PERUBAHAN: Menambahkan parameter df_cloud
def predict_sales(weather_factor=0.5, df_cloud=None):
    try:
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

        csv_path = os.path.abspath(os.path.join(BASE_DIR, '..', 'dataset', 'dataset_penjualan.csv'))
        total_cups_predicted = 150 

        # 1. PRIORITAS SUMBER DATA: Gunakan Cloud jika ada, jika gagal gunakan Lokal
        df = None
        if df_cloud is not None and not df_cloud.empty:
            df = df_cloud.copy()
            print("🧠 AI Menganalisis Data REAL-TIME dari Google Drive!")
        elif os.path.exists(csv_path):
            df = pd.read_csv(csv_path, sep=';')
            print("💻 AI Menganalisis Data LOKAL (Fallback)!")

        # 2. PROSES AI PREDIKSI
        if df is not None and not df.empty:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'], dayfirst=True)
            
            if model is not None and scaler is not None:
                last_7_days = df.tail(7).copy()
                last_7_days['Hari'] = last_7_days['Tanggal'].dt.weekday
                last_7_days['is_weekend'] = last_7_days['Hari'].map(lambda x: 1 if x >= 5 else 0)
                
                sales_data = last_7_days['Total_Produk_Terjual'].values.reshape(-1, 1)
                scaled_sales = scaler.transform(sales_data)
                scaled_weekend = last_7_days['is_weekend'].values.reshape(-1, 1)
                
                X_input = np.hstack((scaled_sales, scaled_weekend))
                X_input = X_input.reshape(1, 7, 2) 
                
                pred_scaled = model.predict(X_input, verbose=0)
                total_cups_predicted = scaler.inverse_transform(pred_scaled)[0][0]
            else:
                # --- FALLBACK CERDAS UNTUK LINGKUNGAN VERCEL SERVERLESS Tanpa TF ---
                recent_sales = df.tail(5)['Total_Produk_Terjual'].values
                if len(recent_sales) == 5:
                    total_cups_predicted = np.average(recent_sales, weights=[0.1, 0.1, 0.2, 0.2, 0.4])
                else:
                    total_cups_predicted = np.mean(recent_sales)

        # 3. Pengaruh Faktor Cuaca Terhadap Multiplier Koefisien Penjualan
        weather_multiplier = 1.0
        is_raining = weather_factor <= 0.4
        if weather_factor >= 0.8: 
            weather_multiplier = 1.1
        elif is_raining: 
            weather_multiplier = 0.7

        # 4. Gabungkan Logika Campuran (Adaptif & Fixed untuk Buah Satuan)
        results = []
        buah_tetap = ['Nenas', 'Melon', 'Semangka', 'Nanas']

        for name, config in min_stock_config.items():
            ai_demand = total_cups_predicted * config['ratio'] * weather_multiplier
            
            if any(b in name for b in buah_tetap):
                final_target = 2 
            elif is_raining:
                final_target = max(1, ai_demand)
            else:
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