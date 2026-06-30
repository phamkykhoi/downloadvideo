#!/usr/bin/env bash
# Tạo _vocal.mp4: video giữ hình, audio chỉ còn nhạc nền (tách giọng bằng demucs).
#
# Khác với LittleCat extract_mp3.sh (_vocal = copy video gốc).
#
# Usage:
#   ./create_vocal_instrumental.sh              # xử lý MrKellyClass/cut/
#   ./create_vocal_instrumental.sh path/to/dir  # thư mục khác

set -euo pipefail

DIR="${1:-$(cd "$(dirname "$0")/cut" && pwd)}"
DEMUCS_OUT="${DIR}/.demucs_tmp"
DEMUCS="${DEMUCS:-demucs}"

if ! command -v "$DEMUCS" >/dev/null 2>&1; then
  echo "Không tìm thấy demucs. Cài: pip install demucs" >&2
  exit 1
fi

if [[ ! -d "$DIR" ]]; then
  echo "Thư mục không tồn tại: $DIR" >&2
  exit 1
fi

cleanup() { rm -rf "$DEMUCS_OUT"; }
trap cleanup EXIT

shopt -s nullglob
for f in "$DIR"/*.mp4; do
  name="$(basename "$f")"
  [[ "$name" == *"_vocal.mp4" ]] && continue

  base="${f%.mp4}"
  stem="$(basename "$base")"
  vocal="${base}_vocal.mp4"

  if [[ -f "$vocal" ]]; then
    echo "==> Bỏ qua (đã có): $(basename "$vocal")"
    continue
  fi

  echo "==> $name — tách giọng (demucs)..."
  rm -rf "$DEMUCS_OUT"
  mkdir -p "$DEMUCS_OUT"

  "$DEMUCS" --two-stems vocals -n htdemucs -o "$DEMUCS_OUT" "$f" >/dev/null

  no_vocals="$DEMUCS_OUT/htdemucs/$stem/no_vocals.wav"
  if [[ ! -f "$no_vocals" ]]; then
    echo "    Lỗi: không có no_vocals.wav" >&2
    exit 1
  fi

  ffmpeg -y -hide_banner -loglevel error -i "$f" -i "$no_vocals" \
    -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 128k -shortest "$vocal"

  echo "    -> $(basename "$vocal")"
done

echo "Xong."
