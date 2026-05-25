# 📎 Appendix — Architecture Decision Records (ADRs)

This appendix documents the architectural decisions made across **V1, V2, and V3**, showing how the system evolved deliberately from **protocol correctness**, to **data correctness**, to **large-object scalability**.

Later ADRs **supersede** earlier ones where behavior was intentionally refined.

***

## 🧾 ADRs — V1 (Protocol Correctness)

> **V1 focus:** Make the system *speak S3 correctly*.

| ADR ID      | Name                 | Decision                                               | Rationale                           | Superseded By | Others (Not Doing)                 |
| ----------- | -------------------- | ------------------------------------------------------ | ----------------------------------- | ------------- | ---------------------------------- |
| **ADR‑101** | Protocol‑First Scope | Prioritize S3 API shape and responses over performance | Enables early AWS CLI compatibility | ADR‑201       | No streaming, no scalability focus |
| **ADR‑102** | Authentication Model | Accept AWS Signature Version 4 (header‑based)          | Required for AWS CLI                | —             | No IAM policies or authz           |
| **ADR‑103** | Storage Backend      | Use filesystem via SFTP (Paramiko)                     | Simple, debuggable backend          | —             | No object store / DB               |
| **ADR‑104** | Object Mapping       | Bucket → directory, Object → file                      | Direct mental model                 | —             | No virtual namespaces              |
| **ADR‑105** | Metadata Handling    | Store metadata as sidecar files                        | Clean separation of data & metadata | —             | No embedded metadata               |
| **ADR‑106** | Object Operations    | Single‑request PUT/GET/DELETE only                     | Minimal viable lifecycle            | ADR‑201       | No multipart, no Range             |
| **ADR‑107** | Error Semantics      | S3‑style XML errors                                    | Client correctness                  | —             | No custom errors                   |
| **ADR‑108** | Visibility Model     | Object visible immediately after PUT                   | Simplicity in MVP                   | ADR‑315       | No atomic commit guarantees        |

***

## 🧾 ADRs — V2 (Streaming & Data Correctness)

> **V2 focus:** Do not corrupt data under streaming and real client behavior.

| ADR ID      | Name                      | Decision                                                | Rationale                               | Superseded By | Others (Not Doing)             |
| ----------- | ------------------------- | ------------------------------------------------------- | --------------------------------------- | ------------- | ------------------------------ |
| **ADR‑201** | Streaming PUT             | Support streaming uploads                               | Memory safety & correctness             | ADR‑313       | No multipart yet               |
| **ADR‑202** | aws‑chunked Detection     | Detect via `Content-Encoding` OR `x-amz-content-sha256` | Required for AWS CLI + MinIO            | —             | No single‑header assumption    |
| **ADR‑203** | Client Coverage           | Validate with AWS CLI, boto3, and `mc`                  | Different clients expose different bugs | —             | No CLI‑only testing            |
| **ADR‑204** | Data Integrity            | Verify correctness via MD5                              | Empirical proof over assumptions        | —             | No trust in happy paths        |
| **ADR‑205** | Streaming GET (Non‑Range) | Allow sequential GET without Range                      | Works for small objects                 | ADR‑301       | No large download guarantees   |
| **ADR‑206** | Delete Semantics          | Make DELETE idempotent                                  | Matches S3 behavior                     | —             | No strict existence checks     |
| **ADR‑207** | Internal Hygiene          | Hide internal files from listing                        | Prevent metadata leakage                | —             | No client‑visible internals    |
| **ADR‑208** | Async/Sync Boundary       | Buffer only where correctness demands                   | Avoid silent corruption                 | ADR‑313       | No unsafe async→sync streaming |
| **ADR‑209** | Listing Model             | Flat listing with prefix filtering                      | Simplicity & clarity                    | —             | No delimiter hierarchy         |
| **ADR‑210** | Deferred Range GET        | Explicitly defer Range GET                              | Avoid broken downloads                  | ADR‑301       | No partial correctness         |

***

## 🧾 ADRs — V3 (Multipart & Large‑Object Semantics)

> **V3 focus:** Scale safely with large objects and enforce data‑plane invariants.

| ADR ID      | Name                    | Decision                                            | Rationale                    | Superseded By      | Others (Not Doing)        |
| ----------- | ----------------------- | --------------------------------------------------- | ---------------------------- | ------------------ | ------------------------- |
| **ADR‑301** | Multipart State Storage | Store multipart state under `.multipart/<uploadId>` | Simple, isolated, debuggable | —                  | No DB / Redis             |
| **ADR‑302** | Object Visibility       | Parts invisible until completion                    | Prevent partial reads        | —                  | No in‑progress visibility |
| **ADR‑303** | Part Storage Format     | Store each part as independent file                 | Parallel uploads             | —                  | No aggregated temp blobs  |
| **ADR‑304** | UploadId Generation     | Use UUID4                                           | Stateless, collision‑safe    | —                  | No custom generators      |
| **ADR‑305** | Assembly Strategy       | Sequential append + rename                          | Deterministic, memory‑safe   | —                  | No streaming merge        |
| **ADR‑306** | ETag Calculation        | Multipart ETag = MD5(parts)+count                   | SDK compatibility            | —                  | No fake ETags             |
| **ADR‑307** | Concurrency Control     | Semaphore on `UploadPart` only                      | Protect backend              | —                  | No global throttling      |
| **ADR‑308** | Parallel Uploads        | Allow parallel parts                                | Required by clients          | —                  | No serialization          |
| **ADR‑309** | Cleanup Strategy        | Explicit abort only                                 | Predictable lifecycle        | —                  | No TTL cleanup            |
| **ADR‑310** | Delete Semantics        | Abort removes all parts                             | Matches S3                   | —                  | No implicit cleanup       |
| **ADR‑311** | Backend Integration     | Extend SFTP backend                                 | Reuse V2 logic               | —                  | No new abstraction        |
| **ADR‑312** | Part Size Enforcement   | Do not enforce 5MB minimum                          | MVP simplicity               | —                  | No strict validation      |
| **ADR‑313** | Streaming Model         | Reuse V2 streaming pipeline                         | Consistency                  | —                  | No new upload pipeline    |
| **ADR‑314** | Directory Isolation     | `.multipart/` namespace                             | Listing isolation            | —                  | No mixed storage          |
| **ADR‑315** | Completion Atomicity    | Final object visible only after commit              | Prevent partial exposure     | Supersedes ADR‑108 | No partial writes         |

***

## 🔄 ADR Supersession Summary

| Earlier Decision | Superseded By | Reason                           |
| ---------------- | ------------- | -------------------------------- |
| ADR‑101          | ADR‑201       | Streaming correctness introduced |
| ADR‑106          | ADR‑201       | Single PUT replaced by streaming |
| ADR‑108          | ADR‑315       | Atomic visibility enforced       |
| ADR‑205          | ADR‑301       | Range GET + multipart required   |
| ADR‑210          | ADR‑301       | Range GET implemented correctly  |

***

## ✅ Final Notes

* No ADR was silently overridden
* Each version introduced **new invariants**
* Earlier guarantees were preserved or strengthened
* Deferred features were explicit, not accidental

This appendix accurately documents **how and why** the system evolved.