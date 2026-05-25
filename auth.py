import hashlib
import hmac
from urllib.parse import parse_qsl, quote


def canonical_query_string(raw_query: str) -> str:
    if not raw_query:
        return ""

    params = parse_qsl(raw_query, keep_blank_values=True)
    params.sort()

    return "&".join(
        f"{quote(k, safe='~-._')}={quote(v, safe='~-._')}"
        for k, v in params
    )


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

def get_signature_key(key, date_stamp, region, service):
    k_date = sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = sign(k_date, region)
    k_service = sign(k_region, service)
    k_signing = sign(k_service, "aws4_request")
    return k_signing

def verify_sigv4(request, secret):
    auth = request.headers.get("Authorization")
    if not auth:
        return False

    try:
        # Minimal parsing (not full edge-case safe yet)
        parts = dict(item.split("=") for item in auth.replace(",", " ").split() if "=" in item)

        credential = parts["Credential"]
        signed_headers = parts["SignedHeaders"]
        signature = parts["Signature"]

        access_key, date, region, service, _ = credential.split("/")

        # Build canonical request
        method = request.method
        uri = request.url.path
        query = canonical_query_string(request.url.query)

        headers = ""
        for h in signed_headers.split(";"):
            headers += f"{h}:{request.headers.get(h)}\n"

        payload_hash = request.headers.get("x-amz-content-sha256")

        canonical_request = "\n".join([
            method,
            uri,
            query,
            headers,
            signed_headers,
            payload_hash
        ])

        canonical_hash = hashlib.sha256(canonical_request.encode()).hexdigest()

        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256",
            request.headers.get("x-amz-date"),
            f"{date}/{region}/{service}/aws4_request",
            canonical_hash
        ])

        signing_key = get_signature_key(secret, date, region, service)
        computed_sig = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

        return computed_sig == signature

    except Exception:
        return False