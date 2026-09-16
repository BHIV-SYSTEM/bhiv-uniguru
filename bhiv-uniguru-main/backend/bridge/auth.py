import os
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def generate_bridge_token():
    secret = os.getenv("JWT_SECRET", "dev-secret")

    payload = {
        "id": os.getenv("BRIDGE_USER_ID"),
        "email": "bridge@internal.ai",
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(hours=12)
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    return token
