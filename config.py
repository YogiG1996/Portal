import os
from dataclasses import dataclass

@dataclass
class Settings:
    # Map UI labels to DB URIs. Override via environment variables when deploying.
    APP_DBS: dict


def _env_or(default: str, env_name: str) -> str:
    return os.getenv(env_name, default)


# Default to local SQLite files under ./db/
BASE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE, 'db')

settings = Settings(APP_DBS={
    'B2C Fron-end Logs': _env_or(f'sqlite:///{os.path.join(DB_DIR, "b2c_frontend.db")}', 'DB_URI_B2C_FE'),
    'B2C Selfcare Logs': _env_or(f'sqlite:///{os.path.join(DB_DIR, "b2c_selfcare.db")}', 'DB_URI_B2C_SELFCARE'),
    'Magento Logs': _env_or(f'sqlite:///{os.path.join(DB_DIR, "magento.db")}', 'DB_URI_MAGENTO'),
    'TIBCO': _env_or(f'sqlite:///{os.path.join(DB_DIR, "tibco.db")}', 'DB_URI_TIBCO'),
    '6D Logs': _env_or(f'sqlite:///{os.path.join(DB_DIR, "sixd.db")}', 'DB_URI_6D'),
})
