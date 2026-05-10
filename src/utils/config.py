import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = os.getenv("DB_PATH", str(ROOT_DIR / "dagher.duckdb"))

# API Keys
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")