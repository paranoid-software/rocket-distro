#!/usr/bin/env python3
"""
Generate API auth files for JWT, master account, and MongoDB keyfile.

Output (relative to STORAGE_PATH; default ./storage):
  - <STORAGE_PATH>/api/auth/master-account.cookie, signing-keypair.json, verification-keypair.json
  - <STORAGE_PATH>/mongodb/keyfile (for replica set auth)

Usage:
  python3 scripts/generate-api-auth.py
  STORAGE_PATH=/var/lib/rocket python3 scripts/generate-api-auth.py
"""
import base64
import json
import os
import secrets
from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("Install: pip install cryptography")
    raise


def main():
    storage = Path(os.environ.get("STORAGE_PATH", "./storage"))
    base = storage / "api" / "auth"
    base.mkdir(parents=True, exist_ok=True)

    # 1. Master account cookie (shared secret for /accounts/token master flow)
    cookie_path = base / "master-account.cookie"
    secret = secrets.token_hex(32)
    cookie_path.write_text(secret)
    print(f"Created {cookie_path}")

    # 2. RSA keypair for JWT (RS256)
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    priv = key.private_numbers()
    pub = key.public_key().public_numbers()

    def to_b64(n):
        by = n.to_bytes((n.bit_length() + 7) // 8 or 1, "big")
        return base64.urlsafe_b64encode(by).rstrip(b"=").decode("ascii")

    # JWK private (for signing)
    signing_jwk = {
        "kty": "RSA",
        "n": to_b64(pub.n),
        "e": to_b64(pub.e),
        "d": to_b64(priv.d),
        "p": to_b64(priv.p),
        "q": to_b64(priv.q),
        "dp": to_b64(priv.dmp1),
        "dq": to_b64(priv.dmq1),
        "qi": to_b64(priv.iqmp),
    }
    signing_path = base / "signing-keypair.json"
    signing_path.write_text(json.dumps(signing_jwk, indent=2))
    print(f"Created {signing_path}")

    # JWK public (for verification)
    verification_jwk = {
        "kty": "RSA",
        "n": to_b64(pub.n),
        "e": to_b64(pub.e),
    }
    verification_path = base / "verification-keypair.json"
    verification_path.write_text(json.dumps(verification_jwk, indent=2))
    print(f"Created {verification_path}")

    # 3. MongoDB keyfile (replica set auth)
    mongo_dir = storage / "mongodb"
    mongo_dir.mkdir(parents=True, exist_ok=True)
    keyfile_path = mongo_dir / "keyfile"
    keyfile_path.write_text(base64.b64encode(secrets.token_bytes(567)).decode()[:756])
    keyfile_path.chmod(0o400)
    print(f"Created {keyfile_path}")

    print(f"\nDone. Auth in {base}/, keyfile in {mongo_dir}/")


if __name__ == "__main__":
    main()
