#!/usr/bin/env bash
set -euo pipefail

BUCKET="testbucket"
KEY="largefile.bin"
DATA_DIR="/data"

echo "== AWS CLI CreateMultipartUpload Test =="
export MSYS_NO_PATHCONV=1

# ------------------------------------------------
# 1. Create multipart upload
# ------------------------------------------------
UPLOAD_ID=$(
  docker compose run --rm awscli \
    aws s3api create-multipart-upload \
      --bucket "$BUCKET" \
      --key "$KEY" \
      --query UploadId \
      --output text
)

# ------------------------------------------------
# 2. Verify UploadId returned
# ------------------------------------------------
if [ -z "$UPLOAD_ID" ] || [ "$UPLOAD_ID" = "None" ]; then
  echo "❌ ERROR: UploadId not returned"
  exit 1
fi
echo "✅ UploadId returned successfully: $UPLOAD_ID"

# ------------------------------------------------
# 3. Verify backend state (SFTP)
# ------------------------------------------------
if ! docker compose run --rm --entrypoint "" sftp \
  test -d "/home/sftpuser/s3-root/$BUCKET/.multipart/$UPLOAD_ID"; then
  echo "❌ ERROR: Multipart directory not created in backend"
  exit 1
fi
echo "✅ Multipart directory created in backend: /home/sftpuser/s3-root/$BUCKET/.multipart/$UPLOAD_ID"

if ! docker compose run --rm --entrypoint "" sftp \
  test -f "/home/sftpuser/s3-root/$BUCKET/.multipart/$UPLOAD_ID/.meta.json"; then
  echo "❌ ERROR: Multipart metadata file (.meta.json) missing"
  exit 1
fi
echo "✅ Multipart metadata file (.meta.json) exists in backend: /home/sftpuser/s3-root/$BUCKET/.multipart/$UPLOAD_ID/.meta.json"

# ================================================================
echo
echo "== AWS CLI UploadPart Test (Single Part) =="

PART_FILE="$DATA_DIR/part1.bin"

# ------------------------------------------------
# 4. Generate part payload
# ------------------------------------------------
head -c 1M /dev/urandom > ".$PART_FILE"
echo "✅ Generated part payload: .$PART_FILE"

# ------------------------------------------------
# 5. Upload part 1
# ------------------------------------------------
ETAG=$(
  docker compose run --rm awscli \
    aws s3api upload-part \
      --bucket "$BUCKET" \
      --key "$KEY" \
      --upload-id "$UPLOAD_ID" \
      --part-number 1 \
      --body "/data/part1.bin" \
      --query ETag \
      --output text
)

if [ -z "$ETAG" ] || [ "$ETAG" = "None" ]; then
  echo "❌ ERROR: No ETag returned for UploadPart"
  exit 1
fi
echo "✅ UploadPart succeeded, ETag returned: $ETAG"

# ------------------------------------------------
# 6. Verify part file exists in backend
# ------------------------------------------------
PART_PATH="/home/sftpuser/s3-root/$BUCKET/.multipart/$UPLOAD_ID/part-00001"

if docker compose run --rm --entrypoint "" sftp \
  ls "$PART_PATH" >/dev/null 2>&1; then
  echo "✅ Part file exists in backend: $PART_PATH"
else
  echo "❌ ERROR: Part file missing in backend: $PART_PATH"
  exit 1
fi

# ------------------------------------------------
# 7. Cleanup local part payload
# ------------------------------------------------
rm -f ".$PART_FILE"
echo "✅ Local part payload cleaned up"

echo
echo "== AWS CLI CompleteMultipartUpload Test =="

PARTS_JSON=".$DATA_DIR/parts.json"

# ------------------------------------------------
# 8. Prepare parts.json for completion
# ------------------------------------------------
cat > "$PARTS_JSON" <<EOF
{
  "Parts": [
    {
      "ETag": $ETAG,
      "PartNumber": 1
    }
  ]
}
EOF
echo "✅ Prepared CompleteMultipartUpload payload: $PARTS_JSON"
cat "$PARTS_JSON"

# ------------------------------------------------
# 9. Complete multipart upload
# ------------------------------------------------
COMPLETE_ETAG=$(
  docker compose run --rm awscli \
    aws s3api complete-multipart-upload \
      --bucket "$BUCKET" \
      --key "$KEY" \
      --upload-id "$UPLOAD_ID" \
      --multipart-upload "file:///data/parts.json" \
      --query ETag \
      --output text
)

if [ -z "$COMPLETE_ETAG" ] || [ "$COMPLETE_ETAG" = "None" ]; then
  echo "❌ ERROR: CompleteMultipartUpload did not return ETag"
  exit 1
fi
echo "✅ CompleteMultipartUpload succeeded, final ETag: $COMPLETE_ETAG"

# ------------------------------------------------
# 10. Verify final object exists
# ------------------------------------------------
if docker compose run --rm awscli \
  aws s3api head-object \
    --bucket "$BUCKET" \
    --key "$KEY" >/dev/null 2>&1; then
  echo "✅ Final object exists in bucket: s3://$BUCKET/$KEY"
else
  echo "❌ ERROR: Final object missing after completion"
  exit 1
fi

# ------------------------------------------------
# 11. Verify multipart directory cleaned up
# ------------------------------------------------
if docker compose run --rm --entrypoint "" sftp \
  ls "/home/sftpuser/s3-root/$BUCKET/.multipart/$UPLOAD_ID" >/dev/null 2>&1; then
  echo "❌ ERROR: Multipart directory still exists after completion"
  exit 1
else
  echo "✅ Multipart directory cleaned up after completion"
fi

# ------------------------------------------------
# 12. Cleanup local files
# ------------------------------------------------
rm -f "$PARTS_JSON"
echo "✅ Local multipart metadata cleaned up"


# ------------------------------------------------
# 13. Create multipart upload for abort test
# ------------------------------------------------
UPLOAD_ID=$(
  docker compose run --rm awscli \
    aws s3api create-multipart-upload \
      --bucket "$BUCKET" \
      --key "$KEY" \
      --query UploadId \
      --output text
)

# ------------------------------------------------
# 14. Verify UploadId returned
# ------------------------------------------------
if [ -z "$UPLOAD_ID" ] || [ "$UPLOAD_ID" = "None" ]; then
  echo "❌ ERROR: UploadId not returned"
  exit 1
fi
echo "✅ UploadId returned successfully: $UPLOAD_ID"

# ------------------------------------------------
# 15. Cleanup (AbortMultipartUpload)
# ------------------------------------------------
docker compose run --rm awscli \
  aws s3api abort-multipart-upload \
    --bucket "$BUCKET" \
    --key "$KEY" \
    --upload-id "$UPLOAD_ID" \
    >/dev/null 2>&1

# ------------------------------------------------
# 16. Verify cleanup
# ------------------------------------------------
if docker compose run --rm --entrypoint "" sftp \
  test -d "/home/sftpuser/s3-root/$BUCKET/.multipart/$UPLOAD_ID"; then
  echo "❌ ERROR: Multipart directory not cleaned up after abort"
  exit 1
else
  echo "✅ Multipart directory cleaned up after abort: /home/sftpuser/s3-root/$BUCKET/.multipart/$UPLOAD_ID"
fi

echo "✅ CreateMultipartUpload test passed"