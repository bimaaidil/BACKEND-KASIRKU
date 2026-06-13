import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

if not firebase_admin._apps:
    # 1. Cek apakah ada environment variable dari Vercel
    if os.environ.get('FIREBASE_CREDENTIALS'):
        cred_json = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
        cred = credentials.Certificate(cred_json)
    # 2. Jika tidak ada (berarti sedang dijalankan di laptop lokal)
    else:
        cred = credentials.Certificate("serviceAccountKey.json")
        
    firebase_admin.initialize_app(cred)

db = firestore.client()