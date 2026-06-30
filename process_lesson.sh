#!/usr/bin/env bash
# Xử lý 1 bài học đã cắt: MP3 + vocal + HLS + gom folder.
#
# Trước khi chạy, file phải nằm tại:
#   downloads/<TEN_BAI>.mp4
#
# Usage:
#   ./process_lesson.sh Shapes_11s-2m35s
#   ./process_lesson.sh Animals_6s-4m20s

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Cách dùng: ./process_lesson.sh <TEN_BAI>" >&2
  echo "Ví dụ:     ./process_lesson.sh Shapes_11s-2m35s" >&2
  echo "" >&2
  echo "Cần có file: downloads/<TEN_BAI>.mp4" >&2
  exit 1
fi

BASE="$1"
DIR="${2:-downloads}"
LESSON="$DIR/$BASE"
INPUT="$DIR/$BASE.mp4"
HLS_TIME="${HLS_TIME:-6}"

if [[ ! -f "$INPUT" ]]; then
  echo "Không tìm thấy: $INPUT" >&2
  exit 1
fi

echo "==> $BASE — trích MP3 + vocal"
ffmpeg -y -hide_banner -loglevel error -i "$INPUT" \
  -vn -c:a libmp3lame -q:a 2 "$DIR/$BASE.mp3"
ffmpeg -y -hide_banner -loglevel error -i "$INPUT" \
  -c copy "$DIR/${BASE}_vocal.mp4"

echo "==> $BASE — tạo folder bài học"
mkdir -p "$LESSON/hls" "$LESSON/hls_vocal"
mv -f "$INPUT" "$LESSON/$BASE.mp4"
mv -f "$DIR/$BASE.mp3" "$LESSON/$BASE.mp3"
mv -f "$DIR/${BASE}_vocal.mp4" "$LESSON/${BASE}_vocal.mp4"

create_hls() {
  local input="$1"
  local output_dir="$2"
  local label="$3"

  echo "==> $BASE — HLS $label"
  # Re-encode H.264 + AAC, keyframe mỗi segment — tránh lỗi loop seg_000/seg_001 trên player
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

create_hls "$LESSON/$BASE.mp4" "$LESSON/hls" "video"
create_hls "$LESSON/${BASE}_vocal.mp4" "$LESSON/hls_vocal" "vocal"

echo ""
echo "Xong: $LESSON/"
echo "  $BASE.mp3"
echo "  $BASE.mp4"
echo "  ${BASE}_vocal.mp4"
echo "  hls/index.m3u8"
echo "  hls_vocal/index.m3u8"
