#!/usr/bin/env bash
# Băm HLS cho Mrs. Kelly's Class (file phẳng trong cut/).
#
# MrKellyClass/cut/1-你好.mp4       -> cut/hls/1-你好/index.m3u8
# MrKellyClass/cut/1-你好_vocal.mp4   -> cut/hls_vocal/1-你好/index.m3u8
#
# Usage:
#   ./prepare_hls.sh                    # tất cả bài trong cut/
#   ./prepare_hls.sh 1-你好             # một bài
#   HLS_TIME=6 ./prepare_hls.sh 1-你好

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DIR="${DIR:-$ROOT/cut}"
HLS_TIME="${HLS_TIME:-6}"

create_hls() {
  local input="$1"
  local output_dir="$2"
  local label="$3"

  mkdir -p "$output_dir"
  echo "    HLS $label -> $output_dir/"

  ffmpeg -y -hide_banner -loglevel error -i "$input" \
    -c:v libx264 -profile:v high -level 4.1 -pix_fmt yuv420p -crf 23 -preset medium \
    -g 300 -keyint_min 300 -sc_threshold 0 \
    -force_key_frames "expr:gte(t,n_forced*${HLS_TIME})" \
    -c:a aac -b:a 128k -ar 44100 -ac 2 \
    -af aresample=async=1:first_pts=0 \
    -f hls \
    -hls_time "$HLS_TIME" \
    -hls_playlist_type vod \
    -hls_segment_type fmp4 \
    -hls_flags independent_segments \
    -hls_fmp4_init_filename init.mp4 \
    -hls_segment_filename "${output_dir}/seg_%03d.m4s" \
    "${output_dir}/index.m3u8"
}

process_lesson() {
  local base="$1"
  local mp4="$DIR/${base}.mp4"
  local vocal="$DIR/${base}_vocal.mp4"

  if [[ ! -f "$mp4" ]]; then
    echo "Bỏ qua: không có $mp4" >&2
    return 1
  fi

  echo "==> $base"
  create_hls "$mp4" "$DIR/hls/$base" "video"

  if [[ -f "$vocal" ]]; then
    create_hls "$vocal" "$DIR/hls_vocal/$base" "vocal"
  else
    echo "    Cảnh báo: không có ${base}_vocal.mp4" >&2
  fi
}

if [[ ! -d "$DIR" ]]; then
  echo "Thư mục không tồn tại: $DIR" >&2
  exit 1
fi

if [[ $# -ge 1 ]]; then
  for base in "$@"; do
    base="${base%.mp4}"
    base="${base%_vocal}"
    process_lesson "$base"
  done
else
  shopt -s nullglob
  for f in "$DIR"/*.mp4; do
    name="$(basename "$f")"
    [[ "$name" == *"_vocal.mp4" ]] && continue
    process_lesson "${name%.mp4}"
  done
fi

echo "Xong."
