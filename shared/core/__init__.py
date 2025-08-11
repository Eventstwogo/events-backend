import os

from dotenv import load_dotenv

# Determine environment (default to local if not set)
ENVIRONMENT = os.getenv("ENVIRONMENT", "local").lower()  # local | production

# Load appropriate .env file
env_file = f".env.{ENVIRONMENT}"
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file)
    print(f"[ENV] Loaded {env_file}")
else:
    print(f"[ENV] No env file found for: {ENVIRONMENT}")

# Optional: expose ENVIRONMENT globally
__all__ = ["ENVIRONMENT"]
