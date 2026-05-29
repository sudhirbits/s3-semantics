# S3‑Compatible API (MVP)

A **correctness‑first, S3‑compatible object storage API** (**FastAPI** + **SFTP**), validated end‑to‑end using **real clients** (AWS CLI, boto3, MinIO).

This project is intentionally scoped as an **MVP**: it implements the *smallest viable subset* of S3 required for **real‑world client interoperability**, while preserving **byte‑level correctness**.

***

## 🎯 Project Intent

This is a **learning‑driven, correctness‑first S3 compatibility layer**. 

> It is NOT a production‑ready replacement for Amazon S3.

All source files are licensed under the Apache License 2.0 unless otherwise noted.

**In scope**

* Correct S3 semantics
* Real client compatibility (AWS CLI, boto3, MinIO)
* Multipart uploads
* Range GET
* Byte‑level data integrity

**Out of scope**

* IAM / authz
* Versioning, lifecycle rules, tagging
* Replication, HA, or durability guarantees
* Performance optimizations beyond correctness

***

## 🚀 Quick Start

```bash
docker compose up -d sftp
docker compose up --build s3api

```

```bash
docker compose run --rm awscli aws s3 mb s3://testbucket
docker compose run --rm awscli aws s3 cp /data/sample.txt s3://testbucket/sample.txt
docker compose run --rm awscli aws  s3 cp s3://testbucket/sample.txt /data/sample.copy.txt
diff ./data/sample.txt ./data/sample.copy.txt || echo "ERROR: files differ"
rm ./data/sample.copy.txt
```

### Multipart + Range GET validation

```bash
head -c 10M /dev/urandom > ./data/data.bin
docker compose run --rm awscli aws  s3 cp /data/data.bin s3://testbucket/data.bin
docker compose run --rm awscli aws  s3 cp s3://testbucket/data.bin /data/data.copy.bin
md5sum ./data/data.bin ./data/data.copy.bin
cmp -s ./data/data.bin ./data/data.copy.bin || echo "ERROR: files differ"
rm ./data/*.bin
```

***

## 🧪 Running Unit Tests

Use the `unittest` Docker Compose service to run the repository tests inside the Python container.

From the repo root:

```bash
docker compose run --rm --build unittest

# verbose 
docker compose run --rm --build unittest -v

# specific tests only 
docker compose run --rm --build unittest discover -s /app/utils -p 'test_*.py'
```
***

## 🔄 Version Progression

* **V1** – Protocol correctness (API shape, responses)  
→ docs/V1\_PROTOCOL.md

* **V2** – Streaming & data correctness (CLI, boto3, mc)  
  → docs/V2\_STREAMING.md

* **V3** – Multipart uploads & large‑object support  
  → docs/V3\_MULTIPART.md

* **ADRs** – Versioned architecture decisions  
  → docs/ADRs.md

***

## ✅ Client Compatibility

| Client          | Status |
| --------------- | ------ |
| AWS CLI         | ✅      |
| boto3           | ✅      |
| MinIO (`mc`)    | ✅      |
| curl / browsers | ✅      |

***

## 🏗️ Architecture Overview

* **API layer:** FastAPI (S3‑compatible REST)
* **Storage layer:** SFTP (Paramiko)
* **Object model:**
  * Bucket → directory
  * Object → file
  * Metadata → sidecar JSON
* **Multipart state:** isolated under `.multipart/`

***

## ✅ Correctness & Verification

Correctness is validated empirically, not assumed.

All critical paths are verified using **byte‑level MD5 checks** against:

* uploaded objects
* backend storage
* client downloads

This includes:

* multipart upload assembly
* large downloads via Range GET
* retries and real client behavior (`aws s3 cp`)

Correctness is prioritized over premature optimization.

***

## ❌ Explicitly Out of Scope (V3)

* Hierarchical listings (`CommonPrefixes`)
* Paginated listings (`max-keys`, continuation tokens)
* Multi‑range GET requests
* Conditional GETs (`If‑Match`, `If‑Range`)
* Automatic cleanup of abandoned multipart uploads
* Object versioning or lifecycle rules
* IAM policies or encryption
* Zero‑copy I/O, async pipelines, or connection pooling

***

## 📎 Architecture Decisions

All major design decisions are documented as **versioned ADRs**, including:

* data‑plane invariants
* multipart lifecycle choices
* concurrency controls
* explicit deferrals

See: docs/ADRs.md

***

## ✅ Summary

* V1 made the system **speak S3**
* V2 made it **data‑correct**
* V3 made it **scale safely for large objects**

This project demonstrates that **S3 compatibility is a data‑plane problem**, and correctness must be **proven**, not claimed.

***