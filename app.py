from flask import Flask, jsonify
from flask_cors import CORS 
import os

# Import Blueprints
from routes.karyawan import karyawan_bp
from routes.absensi import absensi_bp
from routes.produk import produk_bp
from routes.transaksi import transaksi_bp
from routes.prediksi import prediksi_bp 

app = Flask(__name__)

# Mengizinkan semua origin agar tidak ada error CORS lagi
CORS(app, resources={r"/api/*": {"origins": "*"}}) 

# Register Blueprints
app.register_blueprint(karyawan_bp, url_prefix='/api/karyawan')
app.register_blueprint(absensi_bp, url_prefix='/api/absensi')
app.register_blueprint(produk_bp, url_prefix='/api/produk')
app.register_blueprint(transaksi_bp, url_prefix='/api/transaksi')
app.register_blueprint(prediksi_bp, url_prefix='/api/prediksi')

@app.route('/')
def home():
    return jsonify({
        "status": "success",
        "message": "Server Kasirku (Flask) Berjalan Normal!"
    })

if __name__ == '__main__':
    # Gunakan host='0.0.0.0' agar lebih stabil diakses dari localhost maupun IP
    app.run(debug=True, host='0.0.0.0', port=5000)