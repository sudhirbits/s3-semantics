
from fastapi import Request


def is_aws_chunked_request(request: Request) -> bool:
    """
    Both AWS CLI and MinIO (mc) signal streaming payloads differently.
    AWS CLI may use Content-Encoding=aws-chunked,
    while mc relies on x-amz-content-sha256=STREAMING-AWS4-HMAC-SHA256-PAYLOAD.
    """
    return (
            request.headers.get("x-amz-content-sha256") ==
            "STREAMING-AWS4-HMAC-SHA256-PAYLOAD"
            or "aws-chunked" in (request.headers.get("Content-Encoding", "")) 
    )

async def stream_and_decode(request: Request):
    buffer = b""

    async for chunk in request.stream():
        buffer += chunk

        while True:
            pos = buffer.find(b"\r\n")
            if pos == -1:
                break

            header = buffer[:pos]
            rest = buffer[pos+2:]

            size_str = header.split(b";")[0]
            
            try:
                size = int(size_str, 16)
            except ValueError:
                raise Exception("Invalid aws-chunked header")

            if len(rest) < size + 2:
                break

            data = rest[:size]
            yield data

            buffer = rest[size+2:]

            if size == 0:
                return