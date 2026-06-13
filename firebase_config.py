import firebase_admin
from firebase_admin import credentials, firestore
import os
import ast

if not firebase_admin._apps:
    env_creds = os.environ.get('FIREBASE_CREDENTIALS')
    
    if env_creds:
        try:
            # Menggunakan ast.literal_eval sebagai pengganti json.loads 
            # untuk membersihkan karakter newline (\n) atau spasi Windows yang rusak
            cred_dict = ast.literal_eval(env_creds)
            cred = credentials.Certificate(cred_dict)
        except Exception as e:
            print(f"⚠️ Gagal memproses format JSON: {e}")
            # Jika ast gagal, biarkan sistem mencoba Certificate langsung
            cred = credentials.Certificate("serviceAccountKey.json")
    else:
        cred = credentials.Certificate("serviceAccountKey.json")
        
    firebase_admin.initialize_app(cred)

db = firestore.client()