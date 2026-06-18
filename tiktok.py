"""
Module để download video từ TikTok
"""

import yt_dlp
import os
from utils import sanitize_title


def download_tiktok(url, output_path="downloads"):
    """
    Download video từ TikTok
    
    Args:
        url: URL của video TikTok
        output_path: Thư mục để lưu video (mặc định: downloads)
    
    Returns:
        Đường dẫn file đã download
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    downloaded_file = None
    
    def progress_hook(d):
        nonlocal downloaded_file
        if d['status'] == 'finished':
            downloaded_file = d.get('filename')
    
    try:
        # Chuẩn hóa URL TikTok
        original_url = url
        if '?' in url:
            base_url = url.split('?')[0]
            if '/video/' in base_url:
                url = base_url
        
        # Thử nhiều cách khác nhau để download TikTok
        # Cách 1: Thử với mobile user agent và extractor args
        common_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.tiktok.com/',
            'Origin': 'https://www.tiktok.com',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        }
        
        # Options để extract info
        extract_opts = {
            'quiet': False,
            'no_warnings': False,
            'extractor_args': {
                'tiktok': {
                    'api_hostname': 'api16-normal-useast5.us.tiktokv.com',
                }
            },
            'http_headers': common_headers,
        }
        
        title = 'video'
        sanitized_title = 'video'
        
        try:
            with yt_dlp.YoutubeDL(extract_opts) as ydl:
                # Lấy thông tin video trước
                info = ydl.extract_info(url, download=False)
                title = info.get('title', '') or info.get('id', '') or info.get('display_id', '') or 'video'
                sanitized_title = sanitize_title(title)
        except Exception as extract_error:
            print(f"Lỗi khi extract info, thử với video ID: {extract_error}")
            # Nếu không lấy được title, thử extract video ID từ URL
            if '/video/' in url:
                video_id = url.split('/video/')[-1]
                sanitized_title = f'tiktok_{video_id}'
        
        # Đảm bảo file output luôn là .mp4
        output_file = os.path.join(output_path, f'{sanitized_title}.mp4')
        
        # Download với nhiều options khác nhau
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_file.replace('.mp4', '.%(ext)s'),
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'progress_hooks': [progress_hook],
            'extractor_args': {
                'tiktok': {
                    'api_hostname': 'api16-normal-useast5.us.tiktokv.com',
                }
            },
            'http_headers': common_headers,
            'quiet': False,
            'no_warnings': False,
        }
        
        # Thử download với URL gốc trước
        download_urls = [url]
        if original_url != url:
            download_urls.append(original_url)
        
        success = False
        last_error = None
        
        for attempt_url in download_urls:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                    print(f"Đang download video từ TikTok: {attempt_url}")
                    ydl_download.download([attempt_url])
                    print("Download thành công!")
                    success = True
                    break
            except Exception as download_error:
                last_error = download_error
                print(f"Thử với URL khác: {download_error}")
                continue
        
        if not success:
            # Nếu tất cả đều fail, raise error cuối cùng
            raise last_error if last_error else Exception("Không thể download video TikTok")
        
        # Tìm file đã download và đảm bảo là .mp4
        final_file = None
        if downloaded_file and os.path.exists(downloaded_file):
            final_file = downloaded_file
        else:
            # Tìm file mới nhất trong thư mục bắt đầu với sanitized_title
            files = [f for f in os.listdir(output_path) 
                    if os.path.isfile(os.path.join(output_path, f)) 
                    and f.startswith(sanitized_title)]
            if files:
                files.sort(key=lambda x: os.path.getmtime(os.path.join(output_path, x)), reverse=True)
                final_file = os.path.join(output_path, files[0])
            else:
                # Fallback: tìm file mới nhất
                all_files = [f for f in os.listdir(output_path) if os.path.isfile(os.path.join(output_path, f))]
                if all_files:
                    all_files.sort(key=lambda x: os.path.getmtime(os.path.join(output_path, x)), reverse=True)
                    final_file = os.path.join(output_path, all_files[0])
        
        # Đảm bảo file có extension .mp4
        if final_file and os.path.exists(final_file):
            if not final_file.endswith('.mp4'):
                # Đổi tên file thành .mp4
                new_file = os.path.splitext(final_file)[0] + '.mp4'
                if os.path.exists(new_file):
                    os.remove(new_file)
                os.rename(final_file, new_file)
                return new_file
            return final_file
        
        # Nếu không tìm thấy, trả về output_file mong đợi
        if os.path.exists(output_file):
            return output_file
        return None
    except Exception as e:
        print(f"Lỗi khi download video TikTok: {e}")
        raise


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Cách sử dụng: python tiktok.py <url>")
        sys.exit(1)
    download_tiktok(sys.argv[1])

