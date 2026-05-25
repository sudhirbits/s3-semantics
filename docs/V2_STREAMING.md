# 🚀 V2 Objectives — “Streaming & Data Correctness”

> V2 upgrades the system to **memory-safe, streaming-capable object handling**, ensuring correctness for moderate object sizes and eliminating data corruption.

***

## ✅ V2 Scope (Defined Boundary)

| Area                 | Scope                        |
| -------------------- | ---------------------------- |
| Streaming PUT        | Chunked and non-chunked      |
| Streaming GET        | Sequential reads (non-Range) |
| Data integrity       | End-to-end correctness       |
| Client compatibility | AWS CLI + MinIO (`mc`)       |
| Internal hygiene     | Cleanup, idempotency         |

***

## ✅ V2 Achieved

* ✅ Streaming PUT using request streams
* ✅ Correct handling of `aws-chunked` payloads
* ✅ Compatibility with both AWS CLI and MinIO (`mc`)
* ✅ Memory-safe uploads (no full buffering for PUT)
* ✅ Data integrity verified via MD5
* ✅ Idempotent delete semantics
* ✅ Internal file filtering (`.meta.json`, temp files)

***

## ❌ Explicitly Out of Scope (V2)

* ❌ Multipart uploads
* ❌ Parallel upload support
* ❌ Range GET
* ❌ Large file downloads via `aws s3 cp`
* ❌ Pagination and delimiter semantics

***

### AWS CLI Client Compatibility
```shell 
head -c 7M /dev/urandom > data/random.bin  # max is 8 MB for avoiding multipart which is not in scope for V2.
MSYS_NO_PATHCONV=1 docker compose run --rm awscli aws s3 cp /data/random.bin s3://testbucket/largefile.bin
MSYS_NO_PATHCONV=1 docker compose run --rm awscli aws s3 cp s3://testbucket/largefile.bin /data/largefile.bin
md5sum ./data/random.bin ./data/largefile.bin

docker compose run --rm awscli aws s3 rm s3://testbucket/largefile.bin
rm ./data/*.bin || true
```

---

### Minio Client Compatibility
```shell
head -c 7M /dev/urandom > data/random.bin  # max is 8 MB for avoiding multipart which is not in scope for V2.
MSYS_NO_PATHCONV=1 docker compose run --rm mc mc cp /data/random.bin local/testbucket/largefile.bin
MSYS_NO_PATHCONV=1 docker compose run --rm mc mc cp local/testbucket/largefile.bin /data/largefile.bin
md5sum ./data/random.bin ./data/largefile.bin

docker compose run --rm mc mc rm local/testbucket/largefile.bin
rm ./data/*.bin || true
```
---