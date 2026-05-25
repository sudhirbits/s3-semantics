#!/usr/bin/env bash
set -euo pipefail

echo "== MinIO (mc) Integration Test =="

BUCKET1="testbucket"
BUCKET2="testbucket2"
FILE="/data/sample.txt"
DOWNLOADED="/data/sample-downloaded-mc.txt"

# Helper
run() {
  echo ">>> $*"
  MSYS_NO_PATHCONV=1 docker compose run --rm mc "$@"
}


# -------------------------------------
# 0. (Optional) Setup alias
# -------------------------------------
echo "Setting up mc alias..."
run sh -c 'mc alias set local "$AWS_ENDPOINT_URL" "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY"'

# -------------------------------------
# 1. List buckets
# -------------------------------------
run mc ls local

# -------------------------------------
# 2. List bucket
# -------------------------------------
run mc ls local/$BUCKET1 || true

# -------------------------------------
# 3. Upload object
# -------------------------------------
run mc cp "$FILE" local/$BUCKET1/sample.txt

# -------------------------------------
# 4. Download object
# -------------------------------------
run mc cp local/$BUCKET1/sample.txt "$DOWNLOADED"

# -------------------------------------
# 5. Validate integrity
# -------------------------------------
echo "Checking file integrity..."
cmp ".$FILE" ".$DOWNLOADED"

# -------------------------------------
# 6. List after upload
# -------------------------------------
run mc ls local/$BUCKET1

# -------------------------------------
# 7. Clean orphan case (safe)
# -------------------------------------
run mc rm local/$BUCKET1/sample.txt || true

# -------------------------------------
# 8. Create new bucket
# -------------------------------------
run mc mb local/$BUCKET2 || true

# -------------------------------------
# 9. Upload to second bucket
# -------------------------------------
run mc cp "$FILE" local/$BUCKET2/sample.txt

# -------------------------------------
# 10. Expect bucket delete to fail
# -------------------------------------
echo "Expecting BucketNotEmpty failure..."

if run mc rb local/$BUCKET2 >/dev/null 2>&1; then
  echo "❌ ERROR: Expected bucket delete to fail"
  exit 1
else
  echo "✅ Correct: bucket not empty"
fi

# -------------------------------------
# 11. Delete object
# -------------------------------------
run mc rm local/$BUCKET2/sample.txt

# -------------------------------------
# 12. Bucket delete should now succeed
# -------------------------------------
run mc rb local/$BUCKET2

# -------------------------------------
# Cleanup
# -------------------------------------
rm -f "$DOWNLOADED"
rm -rf ./mc-config/*

echo "== ✅ MinIO Client Test Passed =="
