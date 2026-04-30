import firebase_admin
from firebase_admin import credentials, firestore
import os

# Cek apakah sudah ada aplikasi firebase yang berjalan agar tidak error double init
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()