import os
from dotenv import load_dotenv

load_dotenv()  # Loads environment variables from a .env file

SINGLESTORE_API_KEY = os.getenv("SINGLESTORE_API_KEY")
SINGLESTORE_DB_USERNAME = os.getenv("SINGLESTORE_DB_USERNAME")
SINGLESTORE_DB_PASSWORD = os.getenv("SINGLESTORE_DB_PASSWORD")
SINGLESTORE_API_BASE_URL = "https://api.singlestore.com"
