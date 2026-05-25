import uuid
import paramiko
import os
import json
import hashlib

from contextlib import contextmanager
from datetime import datetime, timezone
from stat import S_ISDIR


def is_internal_file(name):
    return name.startswith(".") or name.endswith(".meta.json") or name.endswith(".uploading")


def cleanup_empty_dirs(sftp, bucket_root, path):
    """
    Removes empty directories recursively up to bucket_root (exclusive).
    """
    while path != bucket_root:
        try:
            if sftp.listdir(path):
                break  # directory not empty → stop

            sftp.rmdir(path)
            path = os.path.dirname(path)

        except Exception:
            break  # safe exit on any issue


def write_file_using_chunked_iter(sftp, file_path, chunk_iter):
    hasher = hashlib.md5()
    size = 0
    with sftp.file(file_path, "wb") as f:
        for chunk in chunk_iter:
            f.write(chunk)
            hasher.update(chunk)
            size += len(chunk)

    return hasher, size


class SFTPFile:
    def __init__(self, f, transport, sftp) -> None:
        self._f = f
        self._transport = transport
        self._sftp = sftp

    def read_chunk(self, chunk_size):
        return self._f.read(chunk_size)
    
    
    def seek(self, offset: int):
        self._f.seek(offset)
    
    def close(self):
        self._f.close()
        self._sftp.close()
        self._transport.close()


class SFTPBackend:
    def __init__(self, config):
        self.cfg = config

    def _connect(self):
        transport = paramiko.Transport((self.cfg["host"], self.cfg["port"]))
        transport.connect(
            username=self.cfg["username"],
            password=self.cfg["password"]
        )
        sftp = paramiko.SFTPClient.from_transport(transport)
        return transport, sftp
    
    @contextmanager
    def _sftp(self):
        transport, sftp = self._connect()

        try:
            yield sftp
        finally:
            sftp.close()
            transport.close()

    def _bucket_path(self, bucket):
        return f"{self.cfg['root']}/{bucket}"

    def _object_path(self, bucket, key):
        return f"{self._bucket_path(bucket)}/{key}"
    
    def _mkdir_p(self, sftp, path):
        dirs = path.split('/')
        current = ""
        for d in dirs:
            current += "/" + d
            try:
                sftp.mkdir(current)
            except:
                pass    

    def _meta_path(self, bucket, key):
        return self._object_path(bucket, key) + ".meta.json"

    def create_bucket(self, bucket):
        with self._sftp() as sftp:
            path = self._bucket_path(bucket)

            try:
                sftp.mkdir(path)
            except IOError:
                return  # idempotent

            meta = {
                "name": bucket,
                "creation_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            }

            with sftp.file(f"{path}/.bucket.meta.json", "w") as f:
                f.write(json.dumps(meta))

    def list_buckets(self):
        with self._sftp() as sftp:
            return sftp.listdir(self.cfg["root"])

    def put_object(self, bucket, key, data: bytes):
        with self._sftp() as sftp:
            path = self._object_path(bucket, key)

            # ensure dirs exist
            self._mkdir_p(sftp, os.path.dirname(path))

            with sftp.file(path, 'wb') as f:
                f.write(data)

            # metadata
            meta = {
                "size": len(data),
                "etag": hashlib.md5(data).hexdigest(),
                "last_modified": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            }

            with sftp.file(path + ".meta.json", 'w') as m:
                m.write(json.dumps(meta))

            return meta
        
    def put_object_stream(self, bucket, key, chunk_iter):
        with self._sftp() as sftp:
            final_path = self._object_path(bucket, key)
            temp_path = final_path + ".uploading"

            self._mkdir_p(sftp, os.path.dirname(final_path))

            try:
                hasher, total_size = write_file_using_chunked_iter(sftp, temp_path, chunk_iter)

                # 1. Try remove existing object ignore if files not exists (overwrite semantics)
                try:
                    sftp.remove(final_path)
                except IOError:
                    pass
                
                # 2. Remove existing metadata (if present)
                try:
                    sftp.remove(final_path + ".meta.json")
                except IOError:
                    pass  # OK if metadata does not exist


                sftp.rename(temp_path, final_path)
                meta = {
                    "size": total_size,
                    "etag": hasher.hexdigest(),
                    "last_modified": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%S.000Z"
                    )
                }

                with sftp.file(final_path + ".meta.json", "w") as m:
                    m.write(json.dumps(meta))

                return meta

            except Exception:
                # ✅ cleanup partial file
                try:
                    sftp.remove(temp_path)
                except Exception:
                    pass
                raise


    def get_object(self, bucket, key):
        with self._sftp() as sftp:
            with sftp.file(self._object_path(bucket, key), 'rb') as f:
                return f.read()


    def delete_object(self, bucket, key):
        object_path = self._object_path(bucket, key)
        meta_path = self._meta_path(bucket, key)
        temp_path = object_path + ".uploading"

        with self._sftp() as sftp:
            # ✅ remove object (idempotent)
            try:
                sftp.remove(object_path)
            except IOError:
                pass

            # ✅ remove metadata (idempotent)
            try:
                sftp.remove(meta_path)
            except IOError:
                pass

            # ✅ remove temp file (important for crash recovery)
            try:
                sftp.remove(temp_path)
            except IOError:
                pass

            cleanup_empty_dirs(sftp, bucket, os.path.dirname(object_path))


    def delete_bucket(self, bucket):
        with self._sftp() as sftp:
            path = self._bucket_path(bucket)

            try:
                entries = sftp.listdir(path)
            except FileNotFoundError:
                return  # already gone (idempotent)

            # Ignore internal metadata files
            user_objects = [
                e for e in entries
                if not is_internal_file(e)
            ]

            if user_objects:
                raise FileExistsError("Bucket is not empty")

            # Remove internal metadata files
            for e in entries:
                sftp.remove(f"{path}/{e}")

            # Now remove the bucket directory
            sftp.rmdir(path)

    def list_objects(self, bucket):
        with self._sftp() as sftp:
            files = sftp.listdir(self._bucket_path(bucket))
            return [
                f for f in files 
                if not is_internal_file(f)
            ]

    def list_objects(self, bucket):
        with self._sftp() as sftp:
            base = self._bucket_path(bucket)
            result = []

            def walk(path, prefix=""):
                for entry in sftp.listdir_attr(path):
                    name = entry.filename

                    if is_internal_file(name):
                        continue

                    full_path = f"{path}/{name}"
                    key = f"{prefix}{name}"

                    if S_ISDIR(entry.st_mode):
                        walk(full_path, key + "/")
                    else:
                        result.append(key)

            walk(base)
            return result

    def load_meta(self, bucket, key):
        with self._sftp() as sftp:
            meta_path = self._meta_path(bucket, key)

            try:
                with sftp.file(meta_path, "r") as f:
                    meta = json.loads(f.read())
            except FileNotFoundError:
                raise FileNotFoundError("Metadata not found")

            # Fill defaults if missing
            if "last_modified" not in meta:
                meta["last_modified"] = datetime.now(timezone.utc).strftime(
                    "%a, %d %b %Y %H:%M:%S GMT"
                )

            return meta

    def load_bucket_meta(self, bucket):
        with self._sftp() as sftp:
            path = f"{self._bucket_path(bucket)}/.bucket.meta.json"

            try:
                with sftp.file(path, "r") as f:
                    return json.loads(f.read())
            except IOError:
                # Backward compatibility for existing buckets
                return {
                    "name": bucket,
                    "creation_date": "1970-01-01T00:00:00.000Z"
                }
            
    def open_object(self, bucket, key):
        """
        Returns an open file handle wrapped in SFTPFile for streaming.
        Caller is responsible for closing it.
        """
        transport, sftp = self._connect()
        try:
            f = sftp.file(self._object_path(bucket, key), "rb")
            return SFTPFile(f, transport, sftp)
        except Exception:
            transport.close()
            sftp.close()
            raise

    def create_multipart_upload(self, bucket, key):
        upload_id = str(uuid.uuid4())

        with self._sftp() as sftp:
            base = f"{self._bucket_path(bucket)}/.multipart"
            upload_path = f"{base}/{upload_id}"

            # ✅ ensure .multipart directory exists
            try:
                sftp.mkdir(base)
            except IOError:
                pass

            # ✅ create upload directory
            sftp.mkdir(upload_path)

            # ✅ metadata (ISO‑8601 UTC, consistent with V2)
            meta = {
                "key": key,
                "created_at": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z"
                )
            }

            # ✅ use .meta.json (aligned with object metadata pattern)
            with sftp.file(f"{upload_path}/.meta.json", "w") as f:
                f.write(json.dumps(meta))

        return upload_id
    
    import hashlib

    def write_upload_part(self, bucket, key, upload_id, part_number, chunk_iter):
        part_name = f"part-{part_number:05d}"  # S3 allows up to 10,000 parts.
        upload_dir = f"{self._bucket_path(bucket)}/.multipart/{upload_id}"

        with self._sftp() as sftp:
            # Ensure upload exists
            try:
                sftp.listdir(upload_dir)
            except IOError:
                raise FileNotFoundError("NoSuchUpload")

            part_path = f"{upload_dir}/{part_name}"
            hasher, size = write_file_using_chunked_iter(sftp, part_path, chunk_iter)

            return {
                "etag": hasher.hexdigest(),
                "size": size
            }

    def complete_multipart_upload(self, bucket, key, upload_id, parts, chunk_size):
        """
        Assemble multipart upload into final object.
        parts: ordered list of (part_number, etag)
        """
        bucket_path = self._bucket_path(bucket)
        upload_dir = f"{bucket_path}/.multipart/{upload_id}"

        with self._sftp() as sftp:
            # Ensure upload exists
            try:
                sftp.listdir(upload_dir)
            except IOError:
                raise FileNotFoundError("NoSuchUpload")

            final_path = self._object_path(bucket, key)
            temp_path = final_path + ".uploading"

            self._mkdir_p(sftp, os.path.dirname(final_path))

            part_md5s = []
            total_size = 0

            try:
                with sftp.file(temp_path, "wb") as out:
                    for part_number, expected_etag in parts:
                        part_name = f"part-{part_number:05d}"
                        part_path = f"{upload_dir}/{part_name}"

                        # Read part
                        hasher = hashlib.md5()
                        size = 0

                        try:
                            with sftp.file(part_path, "rb") as pf:
                                while True:
                                    data = pf.read(chunk_size)
                                    if not data:
                                        break
                                    out.write(data)
                                    hasher.update(data)
                                    size += len(data)
                        except IOError:
                            raise ValueError("InvalidPart")

                        actual_etag = hasher.hexdigest()
                        if actual_etag != expected_etag:
                            raise ValueError("InvalidPart")

                        part_md5s.append(bytes.fromhex(actual_etag))
                        total_size += size

                # Multipart ETag
                final_hasher = hashlib.md5()
                for m in part_md5s:
                    final_hasher.update(m)

                final_etag = f"{final_hasher.hexdigest()}-{len(parts)}"

                # Overwrite semantics
                try:
                    sftp.remove(final_path)
                except IOError:
                    pass
                try:
                    sftp.remove(final_path + ".meta.json")
                except IOError:
                    pass

                sftp.rename(temp_path, final_path)

                meta = {
                    "size": total_size,
                    "etag": final_etag,
                    "last_modified": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%S.000Z"
                    )
                }

                with sftp.file(final_path + ".meta.json", "w") as m:
                    m.write(json.dumps(meta))

                # Cleanup multipart directory
                for name in sftp.listdir(upload_dir):
                    sftp.remove(f"{upload_dir}/{name}")
                sftp.rmdir(upload_dir)

                return meta

            except Exception:
                try:
                    sftp.remove(temp_path)
                except Exception:
                    pass
                raise

    def abort_multipart_upload(self, bucket, upload_id):
        upload_dir = f"{self._bucket_path(bucket)}/.multipart/{upload_id}"

        with self._sftp() as sftp:
            # If upload does not exist → NoSuchUpload
            try:
                entries = sftp.listdir(upload_dir)
            except IOError:
                raise FileNotFoundError("NoSuchUpload")

            # Remove all files in upload directory
            for name in entries:
                sftp.remove(f"{upload_dir}/{name}")

            # Remove upload directory itself
            sftp.rmdir(upload_dir)
