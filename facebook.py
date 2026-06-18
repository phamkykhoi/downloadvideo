"""
Module để download video từ Facebook
"""

import yt_dlp
import os
from utils import sanitize_title


def download_facebook(url, output_path="downloads"):
    """
    Download video từ Facebook
    
    Args:
        url: URL của video Facebook
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
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            # Lấy thông tin video trước
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')
            
            # Sanitize tên file
            sanitized_title = sanitize_title(title)
            
            # Đảm bảo file output luôn là .mp4
            output_file = os.path.join(output_path, f'{sanitized_title}.mp4')
            
            # Download với tên file đã sanitize và format mp4
            ydl_opts = {
                'format': 'best',
                'outtmpl': output_file.replace('.mp4', '.%(ext)s'),
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'progress_hooks': [progress_hook],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                print(f"Đang download video từ Facebook: {url}")
                ydl_download.download([url])
                print("Download thành công!")
                
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
        print(f"Lỗi khi download video Facebook: {e}")
        raise


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Cách sử dụng: python facebook.py <url>")
        sys.exit(1)
    download_facebook(sys.argv[1])

