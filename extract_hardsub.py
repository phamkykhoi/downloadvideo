#!/usr/bin/env python3
"""
Trích sub hardcode (OCR) từ video.

Whisper chỉ nghe audio; script này đọc chữ in sẵn trên frame (pinyin + chữ Hán).
Phù hợp video Little Fox và các bài có sub burn-in ở dưới hoặc trên frame.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

try:
    from paddleocr import PaddleOCR
except ImportError:
    print(
        "Thiếu paddleocr. Cài đặt:\n"
        "  pip install paddleocr paddlepaddle pillow",
        file=sys.stderr,
    )
    sys.exit(1)


COPYRIGHT_PATTERNS = (
    r"copyright",
    r"all rights reserved",
    r"littlefox\.com",
    r"little fox co",
)


@dataclass
class SubtitleEntry:
    start: float
    end: float
    lines: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trích sub hardcode từ video bằng OCR (PaddleOCR)."
    )
    parser.add_argument(
        "input",
        nargs="+",
        help="File video (.mp4) hoặc thư mục chứa video",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="File sub đầu ra (chỉ khi xử lý 1 video). Mặc định: cùng tên video, đổi đuôi",
    )
    parser.add_argument(
        "--format",
        choices=("vtt", "srt"),
        default="vtt",
        help="Định dạng sub (mặc định: vtt)",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=2.0,
        help="Số frame/giây để quét OCR (mặc định: 2)",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=2,
        help="Phóng to vùng crop trước OCR (mặc định: 2)",
    )
    parser.add_argument(
        "--bottom-ratio",
        type=float,
        default=0.85,
        help="Bắt đầu crop vùng sub dưới (tỷ lệ chiều cao, mặc định: 0.85)",
    )
    parser.add_argument(
        "--top-ratio",
        type=float,
        default=0.45,
        help="Kết thúc crop vùng sub trên (tỷ lệ chiều cao, mặc định: 0.45)",
    )
    return parser.parse_args()


def collect_videos(paths: list[str]) -> list[Path]:
    videos: list[Path] = []
    for raw in paths:
        path = Path(raw.strip())
        if path.is_dir():
            videos.extend(sorted(path.glob("*.mp4")))
        elif path.is_file() and path.suffix.lower() == ".mp4":
            videos.append(path)
        else:
            print(f"Bỏ qua: {path}", file=sys.stderr)
    return videos


def probe_duration(video: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def extract_frames(video: Path, out_dir: Path, fps: float) -> list[Path]:
    pattern = out_dir / "frame_%06d.jpg"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-vf",
            f"fps={fps}",
            str(pattern),
        ],
        capture_output=True,
        check=True,
    )
    return sorted(out_dir.glob("frame_*.jpg"))


def crop_region(img: Image.Image, region: str, bottom_ratio: float, top_ratio: float) -> Image.Image:
    w, h = img.size
    if region == "bottom":
        crop = img.crop((0, int(h * bottom_ratio), w, h))
    else:
        crop = img.crop((0, 0, w, int(h * top_ratio)))
    return crop


def upscale(img: Image.Image, scale: int) -> Image.Image:
    if scale <= 1:
        return img
    return img.resize((img.width * scale, img.height * scale), Image.LANCZOS)


def sorted_ocr_lines(result: dict) -> list[str]:
    texts = result.get("rec_texts") or []
    boxes = result.get("rec_boxes")
    if not texts:
        return []
    if boxes is None or len(boxes) != len(texts):
        return [t.strip() for t in texts if t.strip()]

    pairs = []
    for text, box in zip(texts, boxes):
        text = text.strip()
        if not text:
            continue
        y = float(box[1]) if hasattr(box, "__getitem__") else float(box[1])
        pairs.append((y, text))
    pairs.sort(key=lambda item: item[0])
    return [text for _, text in pairs]


def ocr_region(ocr: PaddleOCR, img: Image.Image, cache_path: Path) -> list[str]:
    img.save(cache_path)
    result = ocr.predict(str(cache_path))
    if not result:
        return []
    return sorted_ocr_lines(result[0])


def has_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def is_junk(text: str) -> bool:
    lowered = text.lower()
    if any(re.search(pattern, lowered) for pattern in COPYRIGHT_PATTERNS):
        return True
    if lowered.strip() in {"chinese.littlefox.com", "www.littlefox.com"}:
        return True
    return False


def normalize_block(lines: list[str]) -> str:
    return "\n".join(line.strip() for line in lines if line.strip())


def chinese_signature(lines: list[str]) -> str:
    chinese = [ln.strip() for ln in lines if has_chinese(ln)]
    if chinese:
        return "|".join(re.sub(r"\s+", "", ln) for ln in chinese)
    return normalize_block(lines)


def pick_better_lines(current: list[str], candidate: list[str]) -> list[str]:
    if len(chinese_lines(candidate)) > len(chinese_lines(current)):
        return candidate
    if len(candidate) > len(current):
        return candidate
    if sum(len(line) for line in candidate) > sum(len(line) for line in current):
        return candidate
    return current


def chinese_lines(lines: list[str]) -> list[str]:
    return [line for line in lines if has_chinese(line)]


def is_valid_subtitle(lines: list[str]) -> bool:
    text = normalize_block(lines)
    if is_junk(text):
        return False
    chinese = re.findall(r"[\u4e00-\u9fff]", text)
    if len(chinese) >= 3:
        return True
    if chinese and any(marker in text for marker in (":", "：", "!", "！", ".", "。")):
        return True
    return False


def read_frame_text(
    ocr: PaddleOCR,
    frame_path: Path,
    cache_path: Path,
    scale: int,
    bottom_ratio: float,
    top_ratio: float,
) -> list[str]:
    img = Image.open(frame_path)
    bottom = ocr_region(ocr, upscale(crop_region(img, "bottom", bottom_ratio, top_ratio), scale), cache_path)
    if bottom and (has_chinese("\n".join(bottom)) or len(bottom) >= 2):
        return bottom

    top = ocr_region(ocr, upscale(crop_region(img, "top", bottom_ratio, top_ratio), scale), cache_path)
    return top or bottom


def merge_entries(entries: list[SubtitleEntry]) -> list[SubtitleEntry]:
    if not entries:
        return []

    merged: list[SubtitleEntry] = []
    for entry in entries:
        signature = chinese_signature(entry.lines)
        if merged and chinese_signature(merged[-1].lines) == signature:
            merged[-1].end = entry.end
            merged[-1].lines = pick_better_lines(merged[-1].lines, entry.lines)
        else:
            merged.append(
                SubtitleEntry(start=entry.start, end=entry.end, lines=list(entry.lines))
            )
    return merged


def build_entries(
    frames: list[Path],
    fps: float,
    duration: float,
    ocr: PaddleOCR,
    cache_path: Path,
    scale: int,
    bottom_ratio: float,
    top_ratio: float,
) -> list[SubtitleEntry]:
    entries: list[SubtitleEntry] = []
    prev_signature = ""
    current_lines: list[str] = []
    start = 0.0

    for index, frame_path in enumerate(frames):
        timestamp = index / fps
        lines = read_frame_text(
            ocr,
            frame_path,
            cache_path,
            scale,
            bottom_ratio,
            top_ratio,
        )
        if not is_valid_subtitle(lines):
            continue

        signature = chinese_signature(lines)
        if signature == prev_signature:
            continue

        if prev_signature:
            entries.append(SubtitleEntry(start=start, end=timestamp, lines=current_lines))

        start = timestamp
        prev_signature = signature
        current_lines = lines

    if prev_signature:
        end = max(duration, (len(frames) / fps) if frames else duration)
        entries.append(SubtitleEntry(start=start, end=end, lines=current_lines))

    return merge_entries(entries)


def format_timestamp(seconds: float, fmt: str) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    whole = int(secs)
    millis = int(round((secs - whole) * 1000))
    if millis == 1000:
        whole += 1
        millis = 0
    sep = "." if fmt == "vtt" else ","
    return f"{hours:02d}:{minutes:02d}:{whole:02d}{sep}{millis:03d}"


def write_subtitles(entries: list[SubtitleEntry], output_path: Path, fmt: str) -> None:
    lines: list[str] = []
    if fmt == "vtt":
        lines.append("WEBVTT")
        lines.append("")

    for index, entry in enumerate(entries, start=1):
        start = format_timestamp(entry.start, fmt)
        end = format_timestamp(entry.end, fmt)
        if fmt == "srt":
            lines.append(str(index))
        lines.append(f"{start} --> {end}")
        lines.extend(entry.lines)
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def process_video(
    video: Path,
    output_path: Path | None,
    fmt: str,
    fps: float,
    scale: int,
    bottom_ratio: float,
    top_ratio: float,
) -> Path:
    if output_path is None:
        output_path = video.with_suffix(f".{fmt}")

    print(f"Đang xử lý: {video}")
    duration = probe_duration(video)
    ocr = PaddleOCR(lang="ch")

    with tempfile.TemporaryDirectory(prefix="hardsub_") as tmp:
        tmp_dir = Path(tmp)
        frames = extract_frames(video, tmp_dir, fps)
        cache_path = tmp_dir / "crop.jpg"
        entries = build_entries(
            frames,
            fps,
            duration,
            ocr,
            cache_path,
            scale,
            bottom_ratio,
            top_ratio,
        )

    write_subtitles(entries, output_path, fmt)
    print(f"  → {len(entries)} cue, lưu tại {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    videos = collect_videos(args.input)
    if not videos:
        print("Không tìm thấy file .mp4 nào.", file=sys.stderr)
        sys.exit(1)

    if args.output and len(videos) != 1:
        print("Chỉ dùng --output khi xử lý 1 video.", file=sys.stderr)
        sys.exit(1)

    for video in videos:
        process_video(
            video,
            Path(args.output) if args.output else None,
            args.format,
            args.fps,
            args.scale,
            args.bottom_ratio,
            args.top_ratio,
        )


if __name__ == "__main__":
    main()
