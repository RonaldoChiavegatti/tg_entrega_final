import hashlib
import json
import subprocess
import uuid
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PRIVATE_KEY = BASE_DIR / "jwt_private.pem"
PUBLIC_KEY = BASE_DIR / "jwt_public.pem"
USER_STORE = DATA_DIR / "users.json"


def hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_rsa_keys():
    if PRIVATE_KEY.exists() and PUBLIC_KEY.exists():
        print("RSA key pair already exists, skipping generation.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating RSA key pair (2048 bits)...")
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(PRIVATE_KEY)],
        check=True,
    )
    subprocess.run(
        ["openssl", "rsa", "-pubout", "-in", str(PRIVATE_KEY), "-out", str(PUBLIC_KEY)],
        check=True,
    )
    print(f"Keys written to {PRIVATE_KEY} and {PUBLIC_KEY}")


def seed_admin_user():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    admin_user = {
        "id": str(uuid.uuid4()),
        "email": "admin@demo.local",
        "password_hash": hash_password("admin"),
        "role": "admin",
        "tenant_id": "demo",
    }

    payload = {"users": [admin_user]}
    USER_STORE.write_text(json.dumps(payload, indent=2))
    print(f"Admin user seeded in {USER_STORE}")


if __name__ == "__main__":
    generate_rsa_keys()
    seed_admin_user()
