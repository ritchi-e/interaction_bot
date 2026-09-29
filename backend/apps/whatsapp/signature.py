import hashlib
import hmac


def verify_meta_signature(app_secret, body, header):
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    digest = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header.split("=", 1)[1], digest)
