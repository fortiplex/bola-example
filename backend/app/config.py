import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "")
    JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_MINUTES: int = int(os.environ.get("JWT_EXPIRATION_MINUTES", "1440"))
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./bola.db")

    def validate(self) -> None:
        if not self.JWT_SECRET:
            raise RuntimeError("JWT_SECRET environment variable is required")
        if len(self.JWT_SECRET) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 characters")


settings = Settings()
