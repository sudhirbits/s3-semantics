# 🚀 V1 Objectives — “Protocol Correctness”

> V1 establishes a **syntactically correct S3-compatible API surface**, sufficient for basic client interaction, without guarantees on scalability or streaming performance.

***

## ✅ V1 Scope (Defined Boundary)

| Area              | Scope                                  |
| ----------------- | -------------------------------------- |
| API shape         | S3-style REST endpoints                |
| Authentication    | Signature parsing (minimal acceptance) |
| Object operations | PUT, GET, DELETE (single request)      |
| Bucket operations | Create, delete, list                   |
| Metadata          | Basic ETag, size, last-modified        |
| Storage           | Filesystem-backed (SFTP)               |

***

## ✅ V1 Achieved

* ✅ AWS CLI and SDK requests are accepted
* ✅ Correct HTTP status codes and XML error formats
* ✅ Objects can be uploaded, retrieved, and deleted
* ✅ Buckets behave correctly at protocol level
* ✅ Metadata stored and returned correctly

***

## ❌ Explicitly Out of Scope (V1)

* ❌ Streaming correctness
* ❌ Multipart uploads
* ❌ Range GET
* ❌ Large object scalability
* ❌ Performance guarantees

***

### AWS CLI Client Compatibility
```shell 
docker compose run --rm awscli aws s3 ls
docker compose run --rm awscli aws s3 ls s3://testbucket

MSYS_NO_PATHCONV=1 docker compose run --rm awscli aws s3 cp /data/sample.txt s3://testbucket/sample.txt
docker compose run --rm awscli aws s3api head-object --bucket testbucket --key sample.txt

MSYS_NO_PATHCONV=1 docker compose run --rm awscli aws s3 cp s3://testbucket/sample.txt /data/sample-downloaded-aws.txt
docker compose run --rm awscli aws s3 ls s3://testbucket
docker compose run --rm awscli aws s3 rm s3://testbucket/sample.txt

docker compose run --rm awscli aws s3 mb s3://testbucket2
MSYS_NO_PATHCONV=1 docker compose run --rm awscli aws s3 cp /data/sample.txt s3://testbucket2/sample.txt
docker compose run --rm awscli aws s3 rb s3://testbucket2  # Should fail, BucketNotEmpty
docker compose run --rm awscli aws s3 rm s3://testbucket2/sample.txt
docker compose run --rm awscli aws s3 rb s3://testbucket2  # Succeeds

rm ./data/sample-downloaded-aws.txt || true
```

or to run automated
```shell 
./tests/aws_cli_tests.sh
```
---
### Minio Client Compatibility
```shell
MSYS_NO_PATHCONV=1 docker compose run --rm mc sh -c 'mc alias set local $AWS_ENDPOINT_URL $AWS_ACCESS_KEY_ID $AWS_SECRET_ACCESS_KEY'  # optional one time setup

docker compose run --rm mc mc ls local
docker compose run --rm mc mc ls local/testbucket
MSYS_NO_PATHCONV=1 docker compose run --rm mc mc cp /data/sample.txt local/testbucket/sample.txt

MSYS_NO_PATHCONV=1 docker compose run --rm mc mc cp local/testbucket/sample.txt /data/sample-downloaded-mc.txt
docker compose run --rm mc mc ls local/testbucket
docker compose run --rm mc mc rm local/testbucket2/sample.txt

docker compose run --rm mc mc mb local/testbucket2
MSYS_NO_PATHCONV=1 docker compose run --rm mc mc cp /data/sample.txt local/testbucket2/sample.txt
docker compose run --rm mc mc rb local/testbucket2  # Should fail, BucketNotEmpty
docker compose run --rm mc mc rm local/testbucket2/sample.txt
docker compose run --rm mc mc rb local/testbucket2  # Succeeds

rm ./data/sample-downloaded-mc.txt || true
rm ./mc-config/* || true  # optional, if you run this, then ensure you run one time setup again.
```
or to run automated
```shell 
./tests/mc_tests.sh
```

---


### boto3 (AWS SDK) Client Compatibility
```shell
docker compose run --rm boto3 python test_s3_smoke.py 
docker compose run --rm boto3  # Integration tests against s3api
```
--- 