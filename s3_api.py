import asyncio
import os


from auth import verify_sigv4
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from utils.xml_utils import *
from utils.date_utils import to_rfc1123_utc
from utils.chunk_utils import is_aws_chunked_request, stream_and_decode
from utils.version_utils import IS_V2_PLUS


CHUNK_SIZE = int(os.getenv("STREAM_CHUNK_SIZE", 64 * 1024))  # 64KB default


MAX_CONCURRENT_PART_UPLOADS = int(
    os.getenv("MAX_CONCURRENT_PART_UPLOADS", "4")
)

upload_part_semaphore = asyncio.Semaphore(
    MAX_CONCURRENT_PART_UPLOADS
)


def headers_from_meta(meta):
    return {
        "Content-Length": str(meta["size"]),
        "ETag": f"\"{meta['etag']}\"",
        "Last-Modified": to_rfc1123_utc(meta["last_modified"])
    }


def bucket_exists(backend, bucket):
    try:
        buckets = backend.list_buckets()
        return bucket in buckets
    except:
        return False
    
def parse_range_header(range_header: str, total_size: int):
    """
    Parse Range: bytes=start-end
    Returns (start, end) inclusive.
    """
    if not range_header.startswith("bytes="):
        raise ValueError("InvalidRange")

    range_spec = range_header[len("bytes="):]

    start_str, end_str = range_spec.split("-", 1)

    if start_str == "":
        # suffix bytes: bytes=-N
        length = int(end_str)
        start = max(total_size - length, 0)
        end = total_size - 1
    else:
        start = int(start_str)
        end = int(end_str) if end_str else total_size - 1

    if start > end or start >= total_size:
        raise ValueError("InvalidRange")

    return start, min(end, total_size - 1)


def handle_request(app, backend, creds):

    async def router(request: Request):
        path = request.url.path.strip("/").split("/", 1)
        prefix = request.query_params.get("prefix")
        is_aws_chunked = is_aws_chunked_request(request)


        # Auth
        auth_header = request.headers.get("Authorization")
        if auth_header:
            access_key = auth_header.split("Credential=")[1].split("/")[0]
            user = creds.get(access_key)
            if not user or not verify_sigv4(request, user["secret"]):
                return Response(error_xml("AccessDenied", "Invalid signature"), status_code=403)
        else:
            return Response(error_xml("AccessDenied", "Missing Authorization header"), status_code=403)

        # ROOT → list buckets
        if request.url.path == "/":
            buckets = backend.list_buckets()

            result = []
            for name in buckets:
                meta = backend.load_bucket_meta(name)
                result.append(meta)

            return Response(
                list_buckets_xml(result),
                media_type="application/xml"
            )

        bucket = path[0]
        key = path[1] if len(path) > 1 else None

        # Bucket ops
        if not key:
            
            if request.method == "HEAD":
                try:
                    backend.list_objects(bucket)
                    return Response(status_code=200)
                except FileNotFoundError:
                    return Response(error_xml("NoSuchBucket", "Bucket not found"), status_code=404)

            if request.method == "PUT":
                backend.create_bucket(bucket)
                return Response(status_code=200)

            
            if request.method == "GET":
                if not bucket_exists(backend, bucket):
                    return Response(
                        error_xml("NoSuchBucket", "The specified bucket does not exist"),
                        status_code=404,
                        media_type="application/xml"
                    )

                objs = backend.list_objects(bucket)
                
                if prefix:
                    objs = [k for k in objs if k.startswith(prefix)]

                
                result = []
                for key in objs:

                    meta = backend.load_meta(bucket, key)
                    result.append({
                        "key": key,
                        "size": meta["size"],
                        "etag": meta["etag"],
                        "last_modified": to_rfc1123_utc(meta["last_modified"]),
                    })

                return Response(
                    list_objects_xml(result),
                    media_type="application/xml"
                )

            if request.method == "POST" and "delete" in request.url.query:
                try:
                    body = await request.body()
                    keys = parse_delete_objects(body)

                    deleted = []
                    for key in keys:
                        backend.delete_object(bucket, key)
                        deleted.append(key)

                    return Response(
                        delete_objects_result_xml(deleted),
                        status_code=200,
                        media_type="application/xml"
                    )

                except Exception:
                    return Response(
                        error_xml("MalformedXML", "Invalid delete XML"),
                        status_code=400,
                        media_type="application/xml"
                    )            
            
            if request.method == "DELETE":
                if not bucket_exists(backend, bucket):
                    return Response(error_xml("NoSuchBucket", "Bucket not found"), status_code=404)

                try:
                    backend.delete_bucket(bucket)
                    return Response(status_code=204)
                except FileExistsError:
                    return Response(
                        error_xml("BucketNotEmpty", "The bucket you tried to delete is not empty"),
                        status_code=409,
                        media_type="application/xml"
                    )

        # Object ops
        if key:
            if request.method == "HEAD":
                try:
                    meta = backend.load_meta(bucket, key)
                    return Response(
                        status_code=200,
                        headers=headers_from_meta(meta)
                    )
                except FileNotFoundError:
                    return Response(
                        error_xml("NoSuchKey", "Object not found"),
                        status_code=404,
                        media_type="application/xml"
                        )
                
            if request.method == "POST" and "uploads" in request.url.query:  # Multipart upload initiation
                if not bucket_exists(backend, bucket):
                    return Response(
                        error_xml("NoSuchBucket", "Bucket not found"),
                        status_code=404,
                        media_type="application/xml"
                    )

                upload_id = backend.create_multipart_upload(bucket, key)

                return Response(
                    create_multipart_upload_xml(bucket, key, upload_id),
                    media_type="application/xml"
                )     
           
            if (
                request.method == "PUT"
                and "uploadId" in request.query_params
                and "partNumber" in request.query_params
            ):  # Multipart UploadPart
                upload_id = request.query_params.get("uploadId")
                part_number = request.query_params.get("partNumber")

                # Validate partNumber
                try:
                    part_number = int(part_number)
                    if part_number <= 0:
                        raise ValueError
                except ValueError:
                    return Response(
                        error_xml("InvalidArgument", "Invalid partNumber"),
                        status_code=400,
                        media_type="application/xml"
                    )

                # Ensure bucket exists
                if not bucket_exists(backend, bucket):
                    return Response(
                        error_xml("NoSuchBucket", "Bucket not found"),
                        status_code=404,
                        media_type="application/xml"
                    )
                
                async with upload_part_semaphore:
                    chunks = []

                    if is_aws_chunked:
                        async for c in stream_and_decode(request):
                            chunks.append(c)
                    else:
                        async for chunk in request.stream():
                            chunks.append(chunk)

                    def chunk_iter():
                        for c in chunks:
                            yield c

                    meta = backend.write_upload_part(bucket, key, upload_id, part_number, chunk_iter())

                    return Response(
                        status_code=200,
                        headers={
                            "ETag": f"\"{meta['etag']}\""
                        }
                    )           
            
            if (
                request.method == "POST"
                and "uploadId" in request.query_params
            ):  # Multipart CompleteMultipartUpload
                upload_id = request.query_params.get("uploadId")

                if not bucket_exists(backend, bucket):
                    return Response(
                        error_xml("NoSuchBucket", "Bucket not found"),
                        status_code=404,
                        media_type="application/xml"
                    )

                body = await request.body()

                try:
                    parts = parse_complete_multipart_upload(body)
                    meta = backend.complete_multipart_upload(
                        bucket, key, upload_id, parts, CHUNK_SIZE
                    )
                except FileNotFoundError:
                    return Response(
                        error_xml("NoSuchUpload", "Multipart upload not found"),
                        status_code=404,
                        media_type="application/xml"
                    )
                except ValueError as e:
                    code = str(e)
                    return Response(
                        error_xml(code, code),
                        status_code=400,
                        media_type="application/xml"
                    )

                return Response(
                    complete_multipart_upload_xml(bucket, key, meta["etag"]),
                    media_type="application/xml"
                )

            # Multipart AbortMultipartUpload
            if (
                request.method == "DELETE"
                and "uploadId" in request.query_params
            ):
                upload_id = request.query_params.get("uploadId")

                if not bucket_exists(backend, bucket):
                    return Response(
                        error_xml("NoSuchBucket", "Bucket not found"),
                        status_code=404,
                        media_type="application/xml"
                    )

                try:
                    backend.abort_multipart_upload(bucket, upload_id)
                except FileNotFoundError:
                    return Response(
                        error_xml("NoSuchUpload", "Multipart upload not found"),
                        status_code=404,
                        media_type="application/xml"
                    )

                # S3 returns 204 No Content
                return Response(status_code=204)

            if request.method == "PUT":
                if not IS_V2_PLUS:  # Assume V1. V1 doesn't support streaming approach.
                    body = await request.body()
                    meta = backend.put_object(bucket, key, body)
                    return Response(headers={"ETag": meta["etag"]})
                else:  # V2+ streaming approach
                    chunks = []
                    if is_aws_chunked:
                        # bridge async → sync
                        async for c in stream_and_decode(request):
                            chunks.append(c)
                    else:
                        async for c in request.stream():
                            chunks.append(c)

                    def chunk_iter():
                        for c in chunks:
                            yield c

                    meta = backend.put_object_stream(bucket, key, chunk_iter())

                    return Response(headers={"ETag": meta["etag"]})


            # if request.method == "GET":
            #     if not IS_V2_PLUS:  # Assume V1. V1 doesn't support streaming approach.
            #         data = backend.get_object(bucket, key)
            #         meta = backend.load_meta(bucket, key)
            #         return Response(
            #             data,
            #             media_type="application/octet-stream", 
            #             headers=headers_from_meta(meta)
            #             )
            #     else:  # V2+ streaming approach
            #         try:                        
            #             sftp_file = backend.open_object(bucket, key)
            #             meta = backend.load_meta(bucket, key)
                        
            #             def stream():
            #                 try:
            #                     while True:
            #                         chunk = sftp_file.read()
            #                         if not chunk:
            #                             break
            #                         yield chunk
            #                 finally:
            #                     # Ensure both file + SFTP connection are closed
            #                     try:
            #                         sftp_file.close()
            #                     except Exception:
            #                         pass

            #             return StreamingResponse(
            #                 stream(),
            #                 media_type="application/octet-stream",
            #                 headers=headers_from_meta(meta)
            #             )

            #         except FileNotFoundError:
            #             return Response(
            #                 error_xml("NoSuchKey", "Object not found"),
            #                 status_code=404,
            #                 media_type="application/xml"
            #             )
            if request.method == "GET":
                if not IS_V2_PLUS:  # Assume V1. V1 doesn't support streaming approach.
                    meta = backend.load_meta(bucket, key)
                    data = backend.get_object(bucket, key)

                    total_size = meta["size"]
                    headers = headers_from_meta(meta)
                    headers["Accept-Ranges"] = "bytes"

                    range_header = request.headers.get("Range")

                    if range_header:
                        try:
                            start, end = parse_range_header(range_header, total_size)
                        except ValueError:
                            return Response(
                                status_code=416,
                                headers={"Content-Range": f"bytes */{total_size}"}
                            )

                        sliced = data[start:end + 1]

                        headers.update({
                            "Content-Range": f"bytes {start}-{end}/{total_size}",
                            "Content-Length": str(len(sliced)),
                        })

                        return Response(
                            sliced,
                            status_code=206,
                            media_type="application/octet-stream",
                            headers=headers,
                        )

                    headers["Content-Length"] = str(total_size)

                    return Response(
                        data,
                        media_type="application/octet-stream",
                        headers=headers,
                    )            
                else:  # V2+ streaming approach
                    meta = backend.load_meta(bucket, key)
                    total_size = meta["size"]

                    range_header = request.headers.get("Range")

                    # Defaults (full object)
                    start = 0
                    end = total_size - 1
                    status_code = 200

                    headers = headers_from_meta(meta)
                    headers["Accept-Ranges"] = "bytes"

                    if range_header:
                        try:
                            start, end = parse_range_header(range_header, total_size)
                            status_code = 206
                            headers["Content-Range"] = f"bytes {start}-{end}/{total_size}"
                        except ValueError:
                            return Response(
                                status_code=416,
                                headers={"Content-Range": f"bytes */{total_size}"}
                            )

                    length = end - start + 1
                    headers["Content-Length"] = str(length)

                    try:
                        sftp_file = backend.open_object(bucket, key)
                        sftp_file.seek(start)
                    except FileNotFoundError:
                        return Response(
                            error_xml("NoSuchKey", "Object not found"),
                            status_code=404,
                            media_type="application/xml"
                        )
                    
                    def stream_sftp_file():
                        remaining = length

                        try:
                            while remaining > 0:
                                chunk_size = min(CHUNK_SIZE, remaining)
                                data = sftp_file.read_chunk(chunk_size)
                                if not data:
                                    break
                                remaining -= len(data)
                                yield data
                        finally:
                            sftp_file.close()

                    return StreamingResponse(
                        stream_sftp_file(),
                        status_code=status_code,
                        media_type="application/octet-stream",
                        headers=headers,
                    )

            if request.method == "DELETE":
                backend.delete_object(bucket, key)
                return Response(status_code=204)

        return Response(error_xml("NotImplemented", "Unsupported"), status_code=400)

    return router
