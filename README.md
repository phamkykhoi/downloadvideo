# Video Downloader

Công cụ download video từ các nền tảng: YouTube, TikTok, Instagram, Facebook

## Cài đặt

```bash
pip install -r requirements.txt
```

Yêu cầu thêm cho xử lý video / upload S3:

- `ffmpeg` — cắt video, trích audio, băm HLS
- `php` + extension `curl` — upload lên Vietnix S3

## Sử dụng

### Download YouTube 1080p (đã dùng)

Lệnh đã dùng để tải video bài học YouTube **1080p** về thư mục `downloads/`:

```bash
cd /Users/khoipham/Data/Projects/downloader

python youtube.py "https://www.youtube.com/watch?v=VIDEO_ID" 1080
```

Hoặc:

```bash
python main/maimain.py youtube "https://www.youtube.com/watch?v=VIDEO_ID" 1080
```

- Mặc định ưu tiên **1080p** (1920×1080), không có thì fallback 720p
- File lưu tại `downloads/<tên_video>.mp4`
- Các bài đã tải thành công: Animals, Body, Clothing, Color, Vegetables, Foods, Fruits, Holidays, Jobs, Transportation…

Nếu YouTube báo bot / yêu cầu đăng nhập:

```bash
YOUTUBE_COOKIES_BROWSER=chrome python youtube.py "https://www.youtube.com/watch?v=VIDEO_ID" 1080
```

Tải 720p (nhẹ hơn, khi không cần full HD):

```bash
python youtube.py "https://www.youtube.com/watch?v=VIDEO_ID" 720
```

### Sử dụng Web Interface

Chạy ứng dụng web:

```bash
python app.py
```

Sau đó mở trình duyệt và truy cập: `http://localhost:5000`

Giao diện web bao gồm:
- Select box để chọn nền tảng (YouTube, TikTok, Instagram, Facebook)
- Input để nhập link video
- Nút Download để bắt đầu tải video

Giao diện web cũng tải YouTube **1080p** mặc định.

### Sử dụng file main

```bash
python main/maimain.py <platform> <url>
```

Ví dụ:
```bash
python main/maimain.py youtube https://www.youtube.com/watch?v=... 1080
python main/maimain.py tiktok https://www.tiktok.com/@user/video/...
python main/maimain.py instagram https://www.instagram.com/p/...
python main/maimain.py facebook https://www.facebook.com/watch/?v=...
```

### Sử dụng từng module riêng lẻ

```bash
python youtube.py <url> [720|1080]
python tiktok.py <url>
python instagram.py <url>
python facebook.py <url>
```

## Xử lý video bài học (cắt → MP3 → HLS → S3)

Quy trình đầy đủ cho video trong `downloads/`:

```
Download YouTube 1080p  →  python youtube.py "<url>" 1080
    → Cắt đoạn (ffmpeg)
    → Trích MP3 + _vocal.mp4
    → Băm HLS + gom vào folder bài học
    → Upload lên Vietnix S3
```

### 1. Cắt video (giữ nguyên chất lượng)

Cắt từ `0:06` đến `2:53`, đặt tên file ngắn gọn:

```bash
ffmpeg -y -i "downloads/video_goc.mp4" \
  -ss 00:00:06 -to 00:02:53 -c copy \
  "downloads/Animals_6s-4m20s.mp4"
```

Ví dụ khác:

```bash
ffmpeg -y -i "downloads/Learn Different Holidays....mp4" \
  -ss 00:00:06 -to 00:02:30 -c copy \
  "downloads/Holidays_Kids_Beginners_6s-2m30s.mp4"
```

### 2. Trích MP3 và tạo file `_vocal.mp4`

Mỗi file `Animals_6s-4m20s.mp4` tạo ra:

- `Animals_6s-4m20s.mp3` — audio tách ra
- `Animals_6s-4m20s_vocal.mp4` — video giữ nguyên giọng + nhạc nền

```bash
./extract_mp3.sh
./extract_mp3.sh downloads
```

### 3. Băm HLS và gom vào folder từng bài

Mỗi bài được chuyển vào folder riêng, kèm segment HLS (fMP4 `.m4s`, giữ codec gốc):

```
downloads/Animals_6s-4m20s/
├── Animals_6s-4m20s.mp4
├── Animals_6s-4m20s_vocal.mp4
├── Animals_6s-4m20s.mp3
├── hls/
│   ├── index.m3u8
│   ├── init.mp4
│   └── seg_*.m4s
└── hls_vocal/
    ├── index.m3u8
    ├── init.mp4
    └── seg_*.m4s
```

```bash
./prepare_hls.sh
./prepare_hls.sh downloads

# Đổi độ dài mỗi segment (mặc định 6 giây)
HLS_TIME=10 ./prepare_hls.sh downloads
```

### 4. Upload lên Vietnix S3

Copy cấu hình S3:

```bash
cp .env.example .env
# Sửa .env với access key, secret key, bucket...
```

Upload toàn bộ folder bài học lên `Stories/LittleCat/Chinese/`:

```bash
./upload_s3.sh --dry-run   # xem trước danh sách file
./upload_s3.sh             # upload thật
```

Hoặc gọi trực tiếp PHP:

```bash
php upload_s3.php
php upload_s3.php --dry-run
php upload_s3.php --downloads downloads
```

Sau khi upload, URL stream HLS (lưu DB) có dạng:

```
https://s3.vn-hcm-1.vietnix.cloud/littlecat/Stories/LittleCat/Chinese/Animals_6s-4m20s/hls/index.m3u8
https://s3.vn-hcm-1.vietnix.cloud/littlecat/Stories/LittleCat/Chinese/Animals_6s-4m20s/hls_vocal/index.m3u8
```

Chỉ cần lưu URL `index.m3u8` — player tự tải `init.mp4` và các `seg_*.m4s`.

### Chạy nhanh toàn bộ pipeline

```bash
python youtube.py "https://www.youtube.com/watch?v=VIDEO_ID" 1080
./extract_mp3.sh downloads
./prepare_hls.sh downloads
./upload_s3.sh
```

## Cấu trúc dự án

```
downloader/
├── main/
│   └── maimain.py      # File main để gọi các module
├── templates/
│   └── index.html      # Giao diện web
├── downloads/          # Video đã tải / đã xử lý
├── app.py              # Flask web application
├── youtube.py          # Module download YouTube
├── tiktok.py           # Module download TikTok
├── instagram.py        # Module download Instagram
├── facebook.py         # Module download Facebook
├── extract_mp3.sh      # Trích MP3 + _vocal.mp4
├── prepare_hls.sh      # Băm HLS, gom folder bài học
├── upload_s3.sh        # Upload lên Vietnix S3 (gọi upload_s3.php)
├── upload_s3.php       # Script upload S3 (PHP + curl)
├── .env.example        # Mẫu cấu hình S3
├── requirements.txt    # Dependencies Python
└── README.md           # Hướng dẫn sử dụng
```

Videos sẽ được lưu vào thư mục `downloads/`

