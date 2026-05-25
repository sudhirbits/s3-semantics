import os
import tempfile
import hashlib
import time
import boto3


def get_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_DEFAULT_REGION"),
    )


def test_s3_basic_flow():
    """
    What this test gives: Complete contract test
    - ✅ ListBuckets
    - ✅ CreateBucket
    - ✅ PutObject
    - ✅ ListObjectsV2
    - ✅ GetObject
    - ✅ HeadObject
    - ✅ DeleteBucket
    """
    s3 = get_client()

    # Use unique bucket to avoid collisions
    bucket = f"testbucket-sdk-{int(time.time())}"
    key = "sdk.txt"
    content = b"hello from boto3"

    # 1. List buckets (should not crash)
    resp = s3.list_buckets()
    assert "Buckets" in resp

    # 2. Create bucket
    s3.create_bucket(Bucket=bucket)

    buckets = [b["Name"] for b in s3.list_buckets()["Buckets"]]
    assert bucket in buckets

    # 3. Upload object
    s3.put_object(Bucket=bucket, Key=key, Body=content)

    # 4. List objects
    resp = s3.list_objects_v2(Bucket=bucket)
    contents = resp.get("Contents", [])
    keys = [obj["Key"] for obj in contents]
    assert key in keys

    # 5. Download object
    obj = s3.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read()
    assert data == content

    # 6. Head object
    meta = s3.head_object(Bucket=bucket, Key=key)
    assert meta["ContentLength"] == len(content)
    assert "ETag" in meta

    # 7. Delete object
    s3.delete_object(Bucket=bucket, Key=key)

    resp = s3.list_objects_v2(Bucket=bucket)
    assert resp.get("KeyCount", 0) == 0 or "Contents" not in resp

    # 8. Delete bucket
    s3.delete_bucket(Bucket=bucket)

    buckets = [b["Name"] for b in s3.list_buckets()["Buckets"]]
    assert bucket not in buckets


def generate_temp_file(size):
    # ✅ Create temp file
    with tempfile.NamedTemporaryFile(dir="/data", delete=False) as tmp:
        file_path = tmp.name
        remaining = size

        while remaining > 0:
            chunk = os.urandom(min(1024 * 1024, remaining))  # 1MB chunks
            tmp.write(chunk)
            remaining -= len(chunk)

    return file_path


def md5_stream(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def test_medium_object_streaming():
    _object_streaming_with_size_mb(7)


def test_large_object_streaming():
    _object_streaming_with_size_mb(10)


def _object_streaming_with_size_mb(size_in_mb):
    s3 = get_client()

    bucket = "testbucket-objectstreaming"
    key = "objectstreaming.bin"

    size = size_in_mb * 1024 * 1024  # 7 MB
    file_path = generate_temp_file(size)

    try:
        # 1. Create bucket
        try:
            s3.create_bucket(Bucket=bucket)
        except Exception:
            pass

        # 2. Upload (streaming)
        with open(file_path, "rb") as f:
            s3.put_object(Bucket=bucket, Key=key, Body=f)

        # 3. Validate metadata
        meta = s3.head_object(Bucket=bucket, Key=key)
        assert meta["ContentLength"] == size

        # 4. Compute local MD5 (streaming)
        local_md5 = md5_stream(file_path)

        # 5. Download + compute remote MD5 (streaming)
        obj = s3.get_object(Bucket=bucket, Key=key)

        h = hashlib.md5()
        while chunk := obj["Body"].read(1024 * 1024):
            h.update(chunk)

        remote_md5 = h.hexdigest()

        # 6. Validate data integrity
        assert local_md5 == remote_md5

    finally:
        # ✅ Cleanup object + bucket
        try:
            s3.delete_object(Bucket=bucket, Key=key)
        except Exception:
            pass

        try:
            s3.delete_bucket(Bucket=bucket)
        except Exception:
            pass

        # ✅ Cleanup temp file
        try:
            os.remove(file_path)
        except Exception:
            pass


def test_prefix_listing():
    s3 = get_client()

    bucket = "testbucket-prefix"

    keys = [
        "foo/a.txt",
        "foo/b.txt",
        "bar/c.txt",
        "other.txt"
    ]

    # Create bucket
    try:
        s3.create_bucket(Bucket=bucket)
    except Exception:
        pass

    # Upload test objects
    for k in keys:
        s3.put_object(Bucket=bucket, Key=k, Body=b"test")

    # ✅ Test prefix "foo/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix="foo/")
    returned = sorted([o["Key"] for o in resp.get("Contents", [])])

    assert returned == sorted(["foo/a.txt", "foo/b.txt"])

    # ✅ Test prefix "bar/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix="bar/")
    returned = sorted([o["Key"] for o in resp.get("Contents", [])])

    assert returned == ["bar/c.txt"]

    # ✅ Test no prefix
    resp = s3.list_objects_v2(Bucket=bucket)
    returned = sorted([o["Key"] for o in resp.get("Contents", [])])

    assert returned == sorted(keys)

    # ✅ Test non-existing prefix
    resp = s3.list_objects_v2(Bucket=bucket, Prefix="zzz/")
    returned = resp.get("Contents", [])

    assert returned == []

    # Cleanup
    for k in keys:
        s3.delete_object(Bucket=bucket, Key=k)
    s3.delete_bucket(Bucket=bucket)
