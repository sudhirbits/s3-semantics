from xml.etree.ElementTree import Element, ParseError, SubElement, fromstring, tostring
from utils.date_utils import to_iso8601_utc


def list_buckets_xml(buckets):
    root = Element("ListAllMyBucketsResult")
    buckets_el = SubElement(root, "Buckets")

    for b in buckets:
        bucket_el = SubElement(buckets_el, "Bucket")
        SubElement(bucket_el, "Name").text = b["name"]
        SubElement(bucket_el, "CreationDate").text = to_iso8601_utc(b["creation_date"])

    return tostring(root)

def list_objects_xml(objects):
    root = Element("ListBucketResult")

    for obj in objects:
        contents = SubElement(root, "Contents")

        SubElement(contents, "Key").text = obj["key"]
        SubElement(contents, "LastModified").text = to_iso8601_utc(obj["last_modified"])
        SubElement(contents, "ETag").text = f"\"{obj['etag']}\""
        SubElement(contents, "Size").text = str(obj["size"])
        SubElement(contents, "StorageClass").text = "STANDARD"

    return tostring(root)

def error_xml(code, message):
    root = Element("Error")
    SubElement(root, "Code").text = code
    SubElement(root, "Message").text = message
    return tostring(root)

def parse_delete_objects(xml_bytes: bytes) -> list[str]:
    """
    Parse S3 DeleteObjects XML and return list of keys.
    """
    root = fromstring(xml_bytes)

    keys = []
    for obj in root.findall("Object"):
        key = obj.findtext("Key")
        if key:
            keys.append(key)

    return keys

def delete_objects_result_xml(deleted_keys: list[str]) -> bytes:
    root = Element("DeleteResult")

    for key in deleted_keys:
        deleted = SubElement(root, "Deleted")
        SubElement(deleted, "Key").text = key

    return tostring(root)


def create_multipart_upload_xml(bucket, key, upload_id):
    root = Element("CreateMultipartUploadResult")
    SubElement(root, "Bucket").text = bucket
    SubElement(root, "Key").text = key
    SubElement(root, "UploadId").text = upload_id
    return tostring(root)


def parse_complete_multipart_upload(xml_bytes: bytes):
    """
    Parse CompleteMultipartUpload XML.
    Returns ordered list of (part_number, etag_without_quotes).
    """
    try:
        root = fromstring(xml_bytes)
    except ParseError:
        raise ValueError("MalformedXML")

    parts = []
    for part in root.findall(".//{*}Part"):
        
        pn = part.findtext("{*}PartNumber")
        etag = part.findtext("{*}ETag")

        if not pn or not etag:
            raise ValueError("InvalidPart")

        try:
            pn = int(pn)
        except ValueError:
            raise ValueError("InvalidPart")

        etag = etag.strip('"')
        parts.append((pn, etag))

    if not parts:
        raise ValueError("InvalidRequest")

    return parts


def complete_multipart_upload_xml(bucket, key, etag):
    root = Element("CompleteMultipartUploadResult")
    SubElement(root, "Location").text = f"/{bucket}/{key}"
    SubElement(root, "Bucket").text = bucket
    SubElement(root, "Key").text = key
    SubElement(root, "ETag").text = f"\"{etag}\""
    return tostring(root)
