from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    singlestore_api_key: str
    api_base_url: str = "https://api.singlestore.com"

    class Config:
        env_file = "config/settings.toml"
        env_file_encoding = 'utf-8'

settings = Settings()

# Headers with authentication
headers = {
    "Authorization": f"Bearer {settings.singlestore_api_key}",
    "Content-Type": "application/json"
}
