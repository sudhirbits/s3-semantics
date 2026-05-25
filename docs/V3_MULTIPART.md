Perfect 👍 — let’s formalize **V3** exactly the way you did for V2: clean, explicit, and contract‑driven.

# 🚀 V3 Objectives — “Complete S3 Write Semantics”

> V3 upgrades the system from single‑request object handling to **true S3 multipart and advanced object semantics**, enabling large‑object uploads, partial transfers, and real‑world client interoperability at scale.

***
| Area                   | Scope (Done)                                                                            | Outcome                                                |
| ---------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **Multipart Upload**   | Create / UploadPart / Complete / Abort ✅<br>Independent part storage, atomic assembly ✅ | Large files supported ✅<br>AWS CLI & `mc` compatible ✅ |
| **Range GET**          | `Range` header ✅<br>`206 Partial Content` ✅<br>Correct slicing ✅                        | Large downloads work (`aws s3 cp`) ✅                   |
| **Listing (V3 scope)** | Flat prefix‑based listing ✅                                                             | AWS CLI & `mc` usable ✅                                |
| **Integrity & ETag**   | Ordered assembly ✅<br>Multipart ETag format ✅<br>No pre‑complete visibility ✅           | Byte‑accurate uploads & downloads ✅                    |

***

### ✅ V3 Outcome

* ✅ Small + large object uploads
* ✅ Parallel multipart uploads
* ✅ Large file downloads via Range GET
* ✅ AWS CLI and MinIO compatibility
* ✅ Practical parity with core S3 behavior
* ✅ Supports real production workflows (backup, sync, streaming)  
* ✅ Enables high‑throughput, parallel uploads  
* ✅ Removes single‑request upload size limits via multipart upload


## ❌ Explicitly Out of Scope (V3)

* ❌ Hierarchical listings (`CommonPrefixes`, delimiter‑based folders)
* ❌ Paginated listings (`max-keys`, continuation tokens)
* ❌ Multi‑range GET requests
* ❌ Cache control headers (Cache-Control, Expires)
* ❌ Conditional GETs (`If‑Match`, `If‑None‑Match`, `If‑Range`)
* ❌ Automatic cleanup of abandoned multipart uploads (TTL / GC)
* ❌ Object lifecycle - versioning, lifecycle rules, or tagging, legal hold / retention policies
* ❌ IAM policies, bucket policies, or fine‑grained authorization
* ❌ Server‑side encryption (SSE‑S3 / SSE‑KMS)
* ❌ Audit logging
* ❌ Performance optimizations (zero‑copy I/O, async pipelines, Connection pooling for SFTP, Adaptive chunk sizing)

***

# ✅ Final takeaway

> V2 made your system **correct**  
> V3 makes your system **complete for real workloads**

### AWS CLI Client Compatibility
```shell 
# beyond 8MB cli switches to using multi part.
head -c 4G /dev/urandom > data/random.bin 
docker compose run --rm awscli aws s3 cp /data/random.bin s3://testbucket/largefile.bin
md5sum data/random.bin && docker compose exec sftp md5sum /home/sftpuser/s3-root/testbucket/largefile.bin
docker compose run --rm awscli aws s3 cp s3://testbucket/largefile.bin /data/largefile.bin
md5sum data/random.bin data/largefile.bin

docker compose run --rm awscli aws s3 rm s3://testbucket/largefile.bin 
rm ./data/*.bin || true
```

---

### Minio Client Compatibility
```shell
# beyond 8MB cli switches to using multi part.
head -c 10M /dev/urandom > data/random.bin  
docker compose run --rm mc mc cp /data/random.bin local/testbucket/largefile.bin
md5sum data/random.bin && docker compose exec sftp md5sum /home/sftpuser/s3-root/testbucket/largefile.bin
docker compose run --rm mc mc cp local/testbucket/largefile.bin /data/largefile.bin
md5sum data/random.bin data/largefile.bin

docker compose run --rm mc mc rm local/testbucket/largefile.bin
rm ./data/*.bin || true
```
---