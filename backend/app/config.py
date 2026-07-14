import os

class Settings:
    # Get values from env with fallbacks
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemma2-9b-it")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/hcp_crm")
    SQLITE_FALLBACK_URL: str = "sqlite:///./hcp_crm.db"

settings = Settings()
