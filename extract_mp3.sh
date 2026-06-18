#!/usr/bin/env bash
# Trích MP3 và tạo bản _vocal.mp4 từ các file MP4 đã cắt.
#
# Kết quả mỗi file Animals_6s-4m20s.mp4:
#   Animals_6s-4m20s.mp3         — audio đã tách ra
#   Animals_6s-4m20s_vocal.mp4   — video giữ nguyên giọng + nhạc nền
#
# Usage:
#   ./extract_mp3.sh
#   ./extract_mp3.sh downloads

set -euo pipefail

DIR="${1:-downloads}"

if [[ ! -d "$DIR" ]]; then
  echo "Thư mục không tồn tại: $DIR" >&2
  exit 1
fi

shopt -s nullglob
for f in "$DIR"/*.mp4; do
  name="$(basename "$f")"
  [[ "$name" == *"_vocal.mp4" ]] && continue

  base="${f%.mp4}"
  mp3="${base}.mp3"
  vocal="${base}_vocal.mp4"

  echo "==> $name"

  ffmpeg -y -hide_banner -loglevel error -i "$f" -vn -c:a libmp3lame -q:a 2 "$mp3"
  ffmpeg -y -hide_banner -loglevel error -i "$f" -c copy "$vocal"

  echo "    -> $(basename "$mp3")"
  echo "    -> $(basename "$vocal")"
done

echo "Xong."
