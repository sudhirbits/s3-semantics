import unittest
import hashlib
import hmac
from types import SimpleNamespace

from auth import canonical_query_string, sign, get_signature_key, verify_sigv4


class DummyRequest:
    def __init__(self, method, path, query, headers):
        self.method = method
        self.url = SimpleNamespace(path=path, query=query)
        self.headers = headers


class TestCanonicalQueryString(unittest.TestCase):

    def test_empty_query(self):
        self.assertEqual(canonical_query_string(""), "",
                         "Empty query must return empty canonical string")

    def test_single_param(self):
        self.assertEqual(canonical_query_string("a=1"), "a=1",
                         "Single query param must be preserved")

    def test_sorted_params(self):
        self.assertEqual(canonical_query_string("b=2&a=1"), "a=1&b=2",
                         "Query params must be sorted lexicographically")

    def test_blank_values_preserved(self):
        self.assertEqual(canonical_query_string("a=&b=2"), "a=&b=2",
                         "Blank query values must be preserved")

    def test_url_encoding(self):
        self.assertEqual(canonical_query_string("a=hello world"),
                         "a=hello%20world",
                         "Query values must be URL encoded correctly")


class TestSigningHelpers(unittest.TestCase):

    def test_sign_deterministic(self):
        self.assertEqual(sign(b"key", "msg"), sign(b"key", "msg"),
                         "sign() must be deterministic")

    def test_signature_key_stable(self):
        k1 = get_signature_key("secret", "20240101", "us-east-1", "s3")
        k2 = get_signature_key("secret", "20240101", "us-east-1", "s3")
        self.assertEqual(k1, k2,
                         "get_signature_key() must be stable for same inputs")


class TestSigV4Verification(unittest.TestCase):

    def _build_signed_request(self, secret):
        payload_hash = hashlib.sha256(b"").hexdigest()

        headers = {
            "Authorization": (
                "AWS4-HMAC-SHA256 "
                "Credential=AKID/20240101/us-east-1/s3/aws4_request, "
                "SignedHeaders=host;x-amz-date;x-amz-content-sha256, "
                "Signature=dummy"
            ),
            "host": "localhost",
            "x-amz-date": "20240101T000000Z",
            "x-amz-content-sha256": payload_hash,
        }

        req = DummyRequest("GET", "/testbucket/test.txt", "", headers)

        canonical_request = "\n".join([
            "GET",
            "/testbucket/test.txt",
            "",
            "host:localhost\n"
            "x-amz-date:20240101T000000Z\n"
            f"x-amz-content-sha256:{payload_hash}\n",
            "host;x-amz-date;x-amz-content-sha256",
            payload_hash,
        ])

        canonical_hash = hashlib.sha256(
            canonical_request.encode()).hexdigest()

        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256",
            headers["x-amz-date"],
            "20240101/us-east-1/s3/aws4_request",
            canonical_hash,
        ])

        signing_key = get_signature_key(
            secret, "20240101", "us-east-1", "s3")

        signature = hmac.new(
            signing_key, string_to_sign.encode(),
            hashlib.sha256).hexdigest()

        headers["Authorization"] = headers["Authorization"].replace(
            "Signature=dummy", f"Signature={signature}")

        return req

    def test_valid_signature(self):
        req = self._build_signed_request("secret")
        self.assertTrue(verify_sigv4(req, "secret"),
                        "Valid SigV4 request must be accepted")

    def test_invalid_signature(self):
        req = self._build_signed_request("secret")
        self.assertFalse(verify_sigv4(req, "wrong"),
                         "Request signed with wrong secret must be rejected")

    def test_missing_authorization(self):
        req = DummyRequest("GET", "/x", "", {})
        self.assertFalse(verify_sigv4(req, "secret"),
                         "Missing Authorization header must be rejected")

    def test_malformed_authorization(self):
        req = DummyRequest("GET", "/x", "", {"Authorization": "invalid"})
        self.assertFalse(verify_sigv4(req, "secret"),
                         "Malformed Authorization header must be rejected")


if __name__ == "__main__":
    unittest.main()