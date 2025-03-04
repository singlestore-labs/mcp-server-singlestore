API_KEY = "5ba26ff44418aacde02ccf2b2fec68ebf31b8e3934affe7f41e62274946796e6"
API_BASE_URL = "https://api.singlestore.com"

# Headers with authentication
headers = {
    "Authorization": f"Bearer {settings.singlestore_api_key}",
    "Content-Type": "application/json"
}
