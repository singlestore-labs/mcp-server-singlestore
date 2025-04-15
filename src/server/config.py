import os
from dotenv import load_dotenv

load_dotenv()

SINGLESTORE_API_KEY = os.getenv("SINGLESTORE_API_KEY")
SINGLESTORE_DB_USERNAME = os.getenv("SINGLESTORE_DB_USERNAME")
SINGLESTORE_DB_PASSWORD = os.getenv("SINGLESTORE_DB_PASSWORD")
SINGLESTORE_API_BASE_URL = "https://api.singlestore.com"
SINGLESTORE_GRAPHQL_PUBLIC_ENDPOINT = "https://backend.singlestore.com/public"

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Auth
CLIENT_ID = "b7dbf19e-d140-4334-bae4-e8cd03614485"
OAUTH_HOST = "https://authsvc.singlestore.com/"
AUTH_TIMEOUT_SECONDS = 60 # In seconds