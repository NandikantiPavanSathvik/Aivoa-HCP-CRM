import os
from dotenv import load_dotenv

# Load .env file from the backend directory
load_dotenv()

class Settings:
    # Get values from env — load_dotenv() above ensures .env is read
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    # llama-3.3-70b-versatile supports tool calling natively via bind_tools()
    MODEL_NAME: str = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/hcp_crm")
    SQLITE_FALLBACK_URL: str = "sqlite:///./hcp_crm.db"

settings = Settings()
