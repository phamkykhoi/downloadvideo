#!/usr/bin/env bash
# Tổ chức mỗi bài học vào 1 folder và băm HLS (giữ nguyên chất lượng gốc).
#
# downloads/Animals_6s-4m20s/
#   Animals_6s-4m20s.mp4
#   Animals_6s-4m20s_vocal.mp4
#   Animals_6s-4m20s.mp3
#   hls/
#     index.m3u8, init.mp4, seg_*.m4s
#   hls_vocal/
#     index.m3u8, init.mp4, seg_*.m4s
#
# Usage:
#   ./prepare_hls.sh
#   ./prepare_hls.sh downloads

set -euo pipefail

DIR="${1:-downloads}"
HLS_TIME="${HLS_TIME:-6}"

if [[ ! -d "$DIR" ]]; then
  echo "Thư mục không tồn tại: $DIR" >&2
  exit 1
fi

create_hls() {
  local input="$1"
  local output_dir="$2"
  local label="$3"

  mkdir -p "$output_dir"
  echo "    HLS $label -> $(basename "$output_dir")/"

  ffmpeg -y -hide_banner -loglevel error -i "$input" \
    -c copy \
    -f hls \
    -hls_time "$HLS_TIME" \
    -hls_playlist_type vod \
    -hls_segment_type fmp4 \
    -hls_flags independent_segments \
    -hls_fmp4_init_filename init.mp4 \
    -hls_segment_filename "${output_dir}/seg_%03d.m4s" \
    "${output_dir}/index.m3u8"
}

shopt -s nullglob
for f in "$DIR"/*.mp4; do
  name="$(basename "$f")"
  [[ "$name" == *"_vocal.mp4" ]] && continue

  base="${name%.mp4}"
  lesson_dir="$DIR/$base"
  mp4="$lesson_dir/${base}.mp4"
  vocal="$lesson_dir/${base}_vocal.mp4"
  mp3="$lesson_dir/${base}.mp3"

  echo "==> $base"

  mkdir -p "$lesson_dir"

  [[ -f "$f" ]] && mv -n "$f" "$mp4"
  [[ -f "$DIR/${base}_vocal.mp4" ]] && mv -n "$DIR/${base}_vocal.mp4" "$vocal"
  [[ -f "$DIR/${base}.mp3" ]] && mv -n "$DIR/${base}.mp3" "$mp3"

  if [[ ! -f "$mp4" ]]; then
    echo "    Bỏ qua: không tìm thấy $mp4" >&2
    continue
  fi

  create_hls "$mp4" "$lesson_dir/hls" "video"

  if [[ -f "$vocal" ]]; then
    create_hls "$vocal" "$lesson_dir/hls_vocal" "vocal"
  else
    echo "    Cảnh báo: không có file _vocal" >&2
  fi
done

echo "Xong."
