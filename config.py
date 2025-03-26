import os
from google.cloud import firestore
from google.oauth2 import service_account

# Set credentials manually (optional if you used env variable)
key_path = "web-app-3931e-de5fadd1ee07.json"
credentials = service_account.Credentials.from_service_account_file(key_path)

# Initialize Firestore
db = firestore.Client(credentials=credentials)
