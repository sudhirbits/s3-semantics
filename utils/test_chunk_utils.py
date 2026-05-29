import unittest
from unittest.mock import Mock

from utils import chunk_utils


class TestChunkUtils(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.request = Mock()
        self.request.headers = {}

    def _make_stream(self, chunks):
        async def stream():
            for chunk in chunks:
                yield chunk
        return stream

    def test_is_aws_chunked_request_with_streaming_sha256(self):
        self.request.headers = {
            "x-amz-content-sha256": "STREAMING-AWS4-HMAC-SHA256-PAYLOAD"
        }
        self.assertTrue(chunk_utils.is_aws_chunked_request(self.request))

    def test_is_aws_chunked_request_with_aws_chunked_content_encoding(self):
        self.request.headers = {"Content-Encoding": "aws-chunked"}
        self.assertTrue(chunk_utils.is_aws_chunked_request(self.request))

    def test_is_aws_chunked_request_returns_false_for_normal_request(self):
        self.request.headers = {"Content-Encoding": "gzip"}
        self.assertFalse(chunk_utils.is_aws_chunked_request(self.request))

    def test_is_aws_chunked_request_with_combined_content_encoding(self):
        self.request.headers = {"Content-Encoding": "gzip, aws-chunked"}
        self.assertTrue(chunk_utils.is_aws_chunked_request(self.request))

    def test_is_aws_chunked_request_returns_false_when_headers_missing(self):
        self.request.headers = {}
        self.assertFalse(chunk_utils.is_aws_chunked_request(self.request))

    async def test_stream_and_decode_single_chunk_payload(self):
        payload = b"4\r\nTest\r\n0\r\n"
        self.request.stream = self._make_stream([payload])

        data = [chunk async for chunk in chunk_utils.stream_and_decode(self.request)]
        self.assertEqual(data, [b"Test"])

    async def test_stream_and_decode_multiple_chunk_payloads(self):
        chunks = [b"4\r\nTe", b"st\r\n3\r\nabc\r\n0\r\n"]
        self.request.stream = self._make_stream(chunks)

        data = [chunk async for chunk in chunk_utils.stream_and_decode(self.request)]
        self.assertEqual(data, [b"Test", b"abc"])

    async def test_stream_and_decode_with_trailing_zero_chunk(self):
        payload = b"5\r\nHello\r\n0\r\n"
        self.request.stream = self._make_stream([payload])

        data = [chunk async for chunk in chunk_utils.stream_and_decode(self.request)]
        self.assertEqual(data, [b"Hello"])

    async def test_stream_and_decode_raises_on_invalid_chunk_header(self):
        self.request.stream = self._make_stream([b"ZZ\r\nbad\r\n"])
        with self.assertRaises(Exception) as context:
            [chunk async for chunk in chunk_utils.stream_and_decode(self.request)]

        self.assertIn("Invalid aws-chunked header", str(context.exception))

    async def test_stream_and_decode_chunk_size_header_split_across_chunks(self):
        chunks = [b"4\r", b"\nTest\r\n0\r\n"]
        self.request.stream = self._make_stream(chunks)

        data = [chunk async for chunk in chunk_utils.stream_and_decode(self.request)]
        self.assertEqual(data, [b"Test"])

    async def test_stream_and_decode_data_and_trailer_split_across_chunks(self):
        chunks = [b"5\r\nHe", b"llo\r", b"\n0\r\n"]
        self.request.stream = self._make_stream(chunks)

        data = [chunk async for chunk in chunk_utils.stream_and_decode(self.request)]
        self.assertEqual(data, [b"Hello"])

    async def test_stream_and_decode_handles_when_missing_terminating_zero_chunk(self):
        self.request.stream = self._make_stream([b"4\r\nTest\r\n"])
        data = [chunk async for chunk in chunk_utils.stream_and_decode(self.request)]
        self.assertEqual(data, [b"Test"])

    async def test_stream_and_decode_handles_on_incomplete_chunk_trailer(self):
        self.request.stream = self._make_stream([b"4\r\nTest"])
        data = [chunk async for chunk in chunk_utils.stream_and_decode(self.request)]
        self.assertEqual(data, [])

    async def test_stream_and_decode_raises_on_missing_chunk_size_crlf(self):
        self.request.stream = self._make_stream([b"4\rTest\r\n0\r\n"])
        with self.assertRaises(Exception):
            [chunk async for chunk in chunk_utils.stream_and_decode(self.request)]


if __name__ == "__main__":
    unittest.main()
