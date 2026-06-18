#!/usr/bin/env bash
# Upload toàn bộ folder bài học trong downloads/ lên Vietnix S3 (PHP, không cần Composer).
#
# Cấu hình trong .env (xem .env.example)
# Đích: s3://littlecat/Stories/LittleCat/Chinese/<lesson>/...
#
# Usage:
#   ./upload_s3.sh
#   ./upload_s3.sh --dry-run

set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
  echo "Thiếu file .env — copy từ .env.example và điền credentials." >&2
  exit 1
fi

php upload_s3.php "$@"
