import unittest
from xml.etree.ElementTree import fromstring
from utils import xml_utils


class TestXmlUtils(unittest.TestCase):
    """Unit tests for xml_utils module."""

    # =========================================================================
    # Tests for list_buckets_xml()
    # =========================================================================

    def test_list_buckets_xml_empty(self):
        """Test list_buckets_xml with empty bucket list."""
        result = xml_utils.list_buckets_xml([])
        root = fromstring(result)
        self.assertEqual(root.tag, "ListAllMyBucketsResult")
        buckets = root.find("Buckets")
        self.assertEqual(len(list(buckets)), 0)

    def test_list_buckets_xml_single_bucket(self):
        """Test list_buckets_xml with single bucket."""
        buckets = [{"name": "test-bucket", "creation_date": "Mon, 01 Jan 2024 00:00:00 GMT"}]
        result = xml_utils.list_buckets_xml(buckets)
        root = fromstring(result)
        bucket_el = root.find("Buckets/Bucket")
        self.assertIsNotNone(bucket_el)
        self.assertEqual(bucket_el.findtext("Name"), "test-bucket")
        self.assertEqual(bucket_el.findtext("CreationDate"), "2024-01-01T00:00:00.000Z")

    def test_list_buckets_xml_multiple_buckets(self):
        """Test list_buckets_xml with multiple buckets."""
        buckets = [
            {"name": "bucket1", "creation_date": "Mon, 01 Jan 2024 00:00:00 GMT"},
            {"name": "bucket2", "creation_date": "Tue, 02 Jan 2024 00:00:00 GMT"},
        ]
        result = xml_utils.list_buckets_xml(buckets)
        root = fromstring(result)
        bucket_elements = root.findall("Buckets/Bucket")
        self.assertEqual(len(bucket_elements), 2)
        self.assertEqual(bucket_elements[0].findtext("Name"), "bucket1")
        self.assertEqual(bucket_elements[1].findtext("Name"), "bucket2")

    # =========================================================================
    # Tests for list_objects_xml()
    # =========================================================================

    def test_list_objects_xml_empty(self):
        """Test list_objects_xml with empty object list."""
        result = xml_utils.list_objects_xml([])
        root = fromstring(result)
        self.assertEqual(root.tag, "ListBucketResult")
        contents = root.findall("Contents")
        self.assertEqual(len(contents), 0)

    def test_list_objects_xml_single_object(self):
        """Test list_objects_xml with single object."""
        objects = [{
            "key": "test-key",
            "last_modified": "Mon, 01 Jan 2024 12:00:00 GMT",
            "etag": "abc123",
            "size": 1024
        }]
        result = xml_utils.list_objects_xml(objects)
        root = fromstring(result)
        contents = root.find("Contents")
        self.assertIsNotNone(contents)
        self.assertEqual(contents.findtext("Key"), "test-key")
        self.assertEqual(contents.findtext("ETag"), '"abc123"')
        self.assertEqual(contents.findtext("Size"), "1024")
        self.assertEqual(contents.findtext("StorageClass"), "STANDARD")

    def test_list_objects_xml_multiple_objects(self):
        """Test list_objects_xml with multiple objects."""
        objects = [
            {"key": "key1", "last_modified": "Mon, 01 Jan 2024 00:00:00 GMT", "etag": "etag1", "size": 100},
            {"key": "key2", "last_modified": "Tue, 02 Jan 2024 00:00:00 GMT", "etag": "etag2", "size": 200},
        ]
        result = xml_utils.list_objects_xml(objects)
        root = fromstring(result)
        contents_list = root.findall("Contents")
        self.assertEqual(len(contents_list), 2)
        self.assertEqual(contents_list[0].findtext("Key"), "key1")
        self.assertEqual(contents_list[1].findtext("Key"), "key2")

    # =========================================================================
    # Tests for error_xml()
    # =========================================================================

    def test_error_xml_access_denied(self):
        """Test error_xml for AccessDenied."""
        result = xml_utils.error_xml("AccessDenied", "Access Denied")
        root = fromstring(result)
        self.assertEqual(root.tag, "Error")
        self.assertEqual(root.findtext("Code"), "AccessDenied")
        self.assertEqual(root.findtext("Message"), "Access Denied")

    def test_error_xml_not_found(self):
        """Test error_xml for NoSuchKey."""
        result = xml_utils.error_xml("NoSuchKey", "The specified key does not exist.")
        root = fromstring(result)
        self.assertEqual(root.findtext("Code"), "NoSuchKey")
        self.assertIn("key does not exist", root.findtext("Message"))

    def test_error_xml_with_special_characters(self):
        """Test error_xml with special characters in message."""
        result = xml_utils.error_xml("InvalidBucketName", "Bucket name contains <invalid> & characters")
        root = fromstring(result)
        self.assertEqual(root.findtext("Code"), "InvalidBucketName")

    # =========================================================================
    # Tests for parse_delete_objects()
    # =========================================================================

    def test_parse_delete_objects_single_key(self):
        """Test parse_delete_objects with single key."""
        xml_bytes = b"""
        <Delete>
            <Object>
                <Key>test-key</Key>
            </Object>
        </Delete>
        """
        result = xml_utils.parse_delete_objects(xml_bytes)
        self.assertEqual(result, ["test-key"])

    def test_parse_delete_objects_multiple_keys(self):
        """Test parse_delete_objects with multiple keys."""
        xml_bytes = b"""
        <Delete>
            <Object>
                <Key>key1</Key>
            </Object>
            <Object>
                <Key>key2</Key>
            </Object>
            <Object>
                <Key>key3</Key>
            </Object>
        </Delete>
        """
        result = xml_utils.parse_delete_objects(xml_bytes)
        self.assertEqual(result, ["key1", "key2", "key3"])

    def test_parse_delete_objects_empty(self):
        """Test parse_delete_objects with no objects."""
        xml_bytes = b"<Delete></Delete>"
        result = xml_utils.parse_delete_objects(xml_bytes)
        self.assertEqual(result, [])

    def test_parse_delete_objects_with_special_characters(self):
        """Test parse_delete_objects with special characters in keys."""
        xml_bytes = b"""
        <Delete>
            <Object>
                <Key>path/to/file.txt</Key>
            </Object>
            <Object>
                <Key>file-with-dash_and_underscore</Key>
            </Object>
        </Delete>
        """
        result = xml_utils.parse_delete_objects(xml_bytes)
        self.assertEqual(len(result), 2)
        self.assertIn("path/to/file.txt", result)

    # =========================================================================
    # Tests for delete_objects_result_xml()
    # =========================================================================

    def test_delete_objects_result_xml_single_key(self):
        """Test delete_objects_result_xml with single key."""
        result = xml_utils.delete_objects_result_xml(["test-key"])
        root = fromstring(result)
        self.assertEqual(root.tag, "DeleteResult")
        deleted = root.find("Deleted")
        self.assertEqual(deleted.findtext("Key"), "test-key")

    def test_delete_objects_result_xml_multiple_keys(self):
        """Test delete_objects_result_xml with multiple keys."""
        result = xml_utils.delete_objects_result_xml(["key1", "key2", "key3"])
        root = fromstring(result)
        deleted_list = root.findall("Deleted")
        self.assertEqual(len(deleted_list), 3)
        keys = [d.findtext("Key") for d in deleted_list]
        self.assertEqual(keys, ["key1", "key2", "key3"])

    def test_delete_objects_result_xml_empty(self):
        """Test delete_objects_result_xml with empty list."""
        result = xml_utils.delete_objects_result_xml([])
        root = fromstring(result)
        deleted_list = root.findall("Deleted")
        self.assertEqual(len(deleted_list), 0)

    # =========================================================================
    # Tests for create_multipart_upload_xml()
    # =========================================================================

    def test_create_multipart_upload_xml(self):
        """Test create_multipart_upload_xml."""
        result = xml_utils.create_multipart_upload_xml("my-bucket", "my-key", "upload-id-123")
        root = fromstring(result)
        self.assertEqual(root.tag, "CreateMultipartUploadResult")
        self.assertEqual(root.findtext("Bucket"), "my-bucket")
        self.assertEqual(root.findtext("Key"), "my-key")
        self.assertEqual(root.findtext("UploadId"), "upload-id-123")

    def test_create_multipart_upload_xml_with_special_chars(self):
        """Test create_multipart_upload_xml with special characters."""
        result = xml_utils.create_multipart_upload_xml("bucket-name", "path/to/file.txt", "uuid-1234")
        root = fromstring(result)
        self.assertEqual(root.findtext("Key"), "path/to/file.txt")

    # =========================================================================
    # Tests for parse_complete_multipart_upload()
    # =========================================================================

    def test_parse_complete_multipart_upload_single_part(self):
        """Test parse_complete_multipart_upload with single part."""
        xml_bytes = b"""
        <CompleteMultipartUpload>
            <Part>
                <PartNumber>1</PartNumber>
                <ETag>"etag-1"</ETag>
            </Part>
        </CompleteMultipartUpload>
        """
        result = xml_utils.parse_complete_multipart_upload(xml_bytes)
        self.assertEqual(result, [(1, "etag-1")])

    def test_parse_complete_multipart_upload_multiple_parts(self):
        """Test parse_complete_multipart_upload with multiple parts."""
        xml_bytes = b"""
        <CompleteMultipartUpload>
            <Part>
                <PartNumber>1</PartNumber>
                <ETag>"etag-1"</ETag>
            </Part>
            <Part>
                <PartNumber>2</PartNumber>
                <ETag>"etag-2"</ETag>
            </Part>
            <Part>
                <PartNumber>3</PartNumber>
                <ETag>"etag-3"</ETag>
            </Part>
        </CompleteMultipartUpload>
        """
        result = xml_utils.parse_complete_multipart_upload(xml_bytes)
        self.assertEqual(result, [(1, "etag-1"), (2, "etag-2"), (3, "etag-3")])

    def test_parse_complete_multipart_upload_empty_raises(self):
        """Test parse_complete_multipart_upload with no parts raises ValueError."""
        xml_bytes = b"<CompleteMultipartUpload></CompleteMultipartUpload>"
        with self.assertRaises(ValueError) as context:
            xml_utils.parse_complete_multipart_upload(xml_bytes)
        self.assertIn("InvalidRequest", str(context.exception))

    def test_parse_complete_multipart_upload_missing_part_number_raises(self):
        """Test parse_complete_multipart_upload with missing PartNumber raises ValueError."""
        xml_bytes = b"""
        <CompleteMultipartUpload>
            <Part>
                <ETag>"etag-1"</ETag>
            </Part>
        </CompleteMultipartUpload>
        """
        with self.assertRaises(ValueError) as context:
            xml_utils.parse_complete_multipart_upload(xml_bytes)
        self.assertIn("InvalidPart", str(context.exception))

    def test_parse_complete_multipart_upload_missing_etag_raises(self):
        """Test parse_complete_multipart_upload with missing ETag raises ValueError."""
        xml_bytes = b"""
        <CompleteMultipartUpload>
            <Part>
                <PartNumber>1</PartNumber>
            </Part>
        </CompleteMultipartUpload>
        """
        with self.assertRaises(ValueError) as context:
            xml_utils.parse_complete_multipart_upload(xml_bytes)
        self.assertIn("InvalidPart", str(context.exception))

    def test_parse_complete_multipart_upload_invalid_part_number_raises(self):
        """Test parse_complete_multipart_upload with non-integer PartNumber raises ValueError."""
        xml_bytes = b"""
        <CompleteMultipartUpload>
            <Part>
                <PartNumber>not-a-number</PartNumber>
                <ETag>"etag-1"</ETag>
            </Part>
        </CompleteMultipartUpload>
        """
        with self.assertRaises(ValueError) as context:
            xml_utils.parse_complete_multipart_upload(xml_bytes)
        self.assertIn("InvalidPart", str(context.exception))

    def test_parse_complete_multipart_upload_malformed_xml_raises(self):
        """Test parse_complete_multipart_upload with malformed XML raises ValueError."""
        xml_bytes = b"<CompleteMultipartUpload><unclosed>"
        with self.assertRaises(ValueError) as context:
            xml_utils.parse_complete_multipart_upload(xml_bytes)
        self.assertIn("MalformedXML", str(context.exception))

    def test_parse_complete_multipart_upload_etag_without_quotes(self):
        """Test parse_complete_multipart_upload strips quotes from ETag."""
        xml_bytes = b"""
        <CompleteMultipartUpload>
            <Part>
                <PartNumber>1</PartNumber>
                <ETag>"abc123"</ETag>
            </Part>
        </CompleteMultipartUpload>
        """
        result = xml_utils.parse_complete_multipart_upload(xml_bytes)
        self.assertEqual(result[0][1], "abc123")

    # =========================================================================
    # Tests for complete_multipart_upload_xml()
    # =========================================================================

    def test_complete_multipart_upload_xml(self):
        """Test complete_multipart_upload_xml."""
        result = xml_utils.complete_multipart_upload_xml("my-bucket", "my-key", "final-etag")
        root = fromstring(result)
        self.assertEqual(root.tag, "CompleteMultipartUploadResult")
        self.assertEqual(root.findtext("Location"), "/my-bucket/my-key")
        self.assertEqual(root.findtext("Bucket"), "my-bucket")
        self.assertEqual(root.findtext("Key"), "my-key")
        self.assertEqual(root.findtext("ETag"), '"final-etag"')

    def test_complete_multipart_upload_xml_with_path(self):
        """Test complete_multipart_upload_xml with nested key path."""
        result = xml_utils.complete_multipart_upload_xml("bucket", "path/to/file.txt", "etag-xyz")
        root = fromstring(result)
        self.assertEqual(root.findtext("Location"), "/bucket/path/to/file.txt")
        self.assertEqual(root.findtext("Key"), "path/to/file.txt")


if __name__ == "__main__":
    unittest.main()