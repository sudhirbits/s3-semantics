import os
import boto3

s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION"),
)


def run():
    print("== Running boto3 S3 tests ==")

    # 1. List buckets
    print("\n1. List buckets")
    resp = s3.list_buckets()
    print(resp["Buckets"])

    # 2. Create bucket
    bucket = "testbucket-sdk"
    print(f"\n2. Creating bucket: {bucket}")
    try:
        s3.create_bucket(Bucket=bucket)
    except Exception as e:
        print("Bucket already exists:", e)

    # 3. Put object
    print("\n3. Upload object")
    s3.put_object(
        Bucket=bucket,
        Key="sdk.txt",
        Body=b"hello from boto3",
    )

    # 4. List objects
    print("\n4. List objects")
    resp = s3.list_objects_v2(Bucket=bucket)
    print(resp.get("Contents", []))

    # 5. Get object
    print("\n5. Download object")
    obj = s3.get_object(Bucket=bucket, Key="sdk.txt")
    print(obj["Body"].read().decode())

    # 6. Head object
    print("\n6. Head object")
    resp = s3.head_object(Bucket=bucket, Key="sdk.txt")
    print(resp["ContentLength"], resp["ETag"])

    print("\n== Tests completed successfully ==")


if __name__ == "__main__":
    run()
