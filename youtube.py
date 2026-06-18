"""
Module để download video từ YouTube
"""

import yt_dlp
import os
from utils import sanitize_title

# Client ưu tiên: mặc định yt-dlp (android_vr + EJS) trả về 720p/1080p qua HLS
_PLAYER_CLIENT_FALLBACKS = [
    None,
    ['android_vr'],
    ['android', 'web'],
    ['android'],
]

# Trình duyệt thử lấy cookies (cần đã đăng nhập YouTube)
_COOKIE_BROWSERS = ['chrome', 'brave', 'edge', 'firefox', 'chromium', 'safari']

# Ưu tiên 1080p, fallback 720p rồi mới xuống chất lượng thấp hơn
_FORMAT_1080 = (
    'bestvideo[height<=1080]+bestaudio/'
    'best[height<=1080]/'
    'bestvideo[height<=720]+bestaudio/'
    'best[height<=720]/'
    'best'
)

_FORMAT_720 = (
    'bestvideo[height<=720]+bestaudio/'
    'best[height<=720]/'
    'best'
)


def _get_cookie_opts_list():
    """Trả về danh sách cấu hình cookies để thử."""
    attempts = []

    cookies_file = os.environ.get('YOUTUBE_COOKIES_FILE', '').strip()
    if cookies_file and os.path.exists(cookies_file):
        attempts.append({'cookiefile': cookies_file})

    browser = os.environ.get('YOUTUBE_COOKIES_BROWSER', '').strip().lower()
    if browser:
        attempts.append({'cookiesfrombrowser': (browser,)})
    else:
        for name in _COOKIE_BROWSERS:
            attempts.append({'cookiesfrombrowser': (name,)})

    # Thử không cookies nếu tất cả browser đều thất bại
    attempts.append({})
    return attempts


def _build_ydl_opts(output_path, progress_hook, player_clients, cookie_opts, max_height=1080):
    opts = {
        'format': _FORMAT_720 if max_height <= 720 else _FORMAT_1080,
        'outtmpl': os.path.join(output_path, '%(id)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'progress_hooks': [progress_hook],
        'remote_components': ['ejs:github'],
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
        },
    }
    opts.update(cookie_opts)
    if player_clients is not None:
        opts['extractor_args'] = {
            'youtube': {'player_client': player_clients},
        }
    return opts


def _cookie_label(cookie_opts):
    if 'cookiefile' in cookie_opts:
        return f"file:{cookie_opts['cookiefile']}"
    if 'cookiesfrombrowser' in cookie_opts:
        return cookie_opts['cookiesfrombrowser'][0]
    return 'no-cookies'


def download_youtube(url, output_path="downloads", max_height=1080):
    """
    Download video từ YouTube

    Args:
        url: URL của video YouTube
        output_path: Thư mục để lưu video (mặc định: downloads)
        max_height: Độ phân giải tối đa (720 hoặc 1080, mặc định: 1080)

    Returns:
        Đường dẫn file đã download
    """
    if max_height not in (720, 1080):
        max_height = 1080

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    downloaded_file = None

    def progress_hook(d):
        nonlocal downloaded_file
        if d['status'] == 'finished':
            downloaded_file = d.get('filename')

    last_error = None

    try:
        for cookie_opts in _get_cookie_opts_list():
            cookie_name = _cookie_label(cookie_opts)

            for player_clients in _PLAYER_CLIENT_FALLBACKS:
                try:
                    ydl_opts = _build_ydl_opts(
                        output_path, progress_hook, player_clients, cookie_opts, max_height
                    )

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        print(f"Đang download ({max_height}p, cookies={cookie_name}): {url}")
                        info = ydl.extract_info(url, download=True)
                        height = info.get('height') or 'unknown'
                        print(f"Download thành công! ({height}p)")

                        title = sanitize_title(info.get('title', 'video'))
                        final_file = downloaded_file

                        if not final_file or not os.path.exists(final_file):
                            video_id = info.get('id', 'video')
                            for ext in ('mp4', 'mkv', 'webm'):
                                candidate = os.path.join(output_path, f'{video_id}.{ext}')
                                if os.path.exists(candidate):
                                    final_file = candidate
                                    break

                        if final_file and os.path.exists(final_file):
                            target_file = os.path.join(output_path, f'{title}.mp4')
                            if final_file != target_file:
                                if os.path.exists(target_file):
                                    os.remove(target_file)
                                os.rename(final_file, target_file)
                            return target_file
                        return None

                except Exception as e:
                    last_error = e
                    downloaded_file = None
                    client_label = player_clients or 'default'
                    err = str(e)
                    if 'bot' in err.lower() or 'sign in' in err.lower():
                        print(f"Cookies {cookie_name} + client {client_label}: bị YouTube chặn bot")
                    else:
                        print(f"Cookies {cookie_name} + client {client_label} thất bại: {e}")
                    continue

        if last_error:
            raise RuntimeError(
                'YouTube yêu cầu xác thực. Hãy đăng nhập YouTube trên Chrome, '
                'hoặc đặt biến môi trường YOUTUBE_COOKIES_BROWSER=chrome '
                '(brave/edge/firefox). Chi tiết: '
                'https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp'
            ) from last_error
        return None
    except Exception as e:
        print(f"Lỗi khi download video YouTube: {e}")
        raise


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Cách sử dụng: python youtube.py <url> [720|1080]")
        sys.exit(1)

    quality = 1080
    if len(sys.argv) >= 3:
        try:
            quality = int(sys.argv[2])
        except ValueError:
            print("Chất lượng phải là 720 hoặc 1080")
            sys.exit(1)

    download_youtube(sys.argv[1], max_height=quality)
