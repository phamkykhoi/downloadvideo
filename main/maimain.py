#!/usr/bin/env python3
"""
Main file để download video từ các nền tảng khác nhau
"""

import sys
import os

# Thêm thư mục gốc vào path để import các module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube import download_youtube
from tiktok import download_tiktok
from instagram import download_instagram
from facebook import download_facebook


def main():
    """Hàm main để xử lý download video"""
    if len(sys.argv) < 3:
        print("Cách sử dụng: python main/maimain.py <platform> <url> [720|1080]")
        print("Platforms: youtube, tiktok, instagram, facebook")
        print("Ví dụ: python main/maimain.py youtube https://www.youtube.com/watch?v=... 1080")
        sys.exit(1)
    
    platform = sys.argv[1].lower()
    url = sys.argv[2]
    max_height = 1080
    if len(sys.argv) >= 4 and platform == "youtube":
        try:
            max_height = int(sys.argv[3])
        except ValueError:
            print("Chất lượng YouTube phải là 720 hoặc 1080")
            sys.exit(1)
    
    try:
        if platform == "youtube":
            download_youtube(url, max_height=max_height)
        elif platform == "tiktok":
            download_tiktok(url)
        elif platform == "instagram":
            download_instagram(url)
        elif platform == "facebook":
            download_facebook(url)
        else:
            print(f"Platform không được hỗ trợ: {platform}")
            print("Các platform được hỗ trợ: youtube, tiktok, instagram, facebook")
            sys.exit(1)
    except Exception as e:
        print(f"Lỗi khi download video: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

