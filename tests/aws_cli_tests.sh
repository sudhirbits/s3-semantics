#!/usr/bin/env bash
set -euo pipefail

echo "== AWS CLI Integration Test =="

BUCKET1="testbucket"
BUCKET2="testbucket2"
FILE="/data/sample.txt"
DOWNLOADED="/data/sample-downloaded-aws.txt"

# Helper
run() {
  echo ">>> $*"
  MSYS_NO_PATHCONV=1 docker compose run --rm awscli "$@"
}

# 1. List buckets
run aws s3 ls

# 2. List bucket contents
run aws s3 ls s3://$BUCKET1 || true

# 3. Upload object
run aws s3 cp "$FILE" s3://$BUCKET1/sample.txt

# 4. HEAD object
run aws s3api head-object --bucket $BUCKET1 --key sample.txt

# 5. Download object
run aws s3 cp s3://$BUCKET1/sample.txt "$DOWNLOADED"

# 6. Verify integrity
echo "Checking file integrity..."
cmp ".$FILE" ".$DOWNLOADED"

# 7. List after upload
run aws s3 ls s3://$BUCKET1

# 8. Delete object
run aws s3 rm s3://$BUCKET1/sample.txt

# 9. Create second bucket
run aws s3 mb s3://$BUCKET2 || true

# 10. Upload into second bucket
run aws s3 cp "$FILE" s3://$BUCKET2/sample.txt

# 11. Bucket delete should fail
echo "Expecting BucketNotEmpty failure..."
if run aws s3 rb s3://$BUCKET2 >/dev/null 2>&1; then
  echo "❌ ERROR: Bucket delete should have failed"
  exit 1
fi

# 12. Remove object
run aws s3 rm s3://$BUCKET2/sample.txt

# 13. Now bucket delete should succeed
run aws s3 rb s3://$BUCKET2

# Cleanup
rm -f ./data/sample-downloaded-aws.txt

echo "== ✅ AWS CLI Test Passed =="