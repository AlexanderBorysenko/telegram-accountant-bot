from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    anthropic_api_key: str
    mongodb_uri: str = "mongodb://mongo:27017"
    mongodb_db_name: str = "buhalter"


settings = Settings()
