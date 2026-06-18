"""
Utility functions cho video downloader
"""

import re
import os


def sanitize_filename(filename, max_length=200):
    """
    Làm sạch và rút gọn tên file để tránh lỗi "File name too long"
    
    Args:
        filename: Tên file gốc
        max_length: Độ dài tối đa (mặc định: 200)
    
    Returns:
        Tên file đã được làm sạch và rút gọn
    """
    # Loại bỏ các ký tự không hợp lệ cho tên file
    # Giữ lại: chữ cái, số, dấu gạch dưới, dấu gạch ngang, dấu chấm, khoảng trắng
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Loại bỏ các ký tự đặc biệt và emoji
    filename = re.sub(r'[^\w\s\-_\.]', '', filename)
    
    # Thay thế nhiều khoảng trắng bằng một khoảng trắng
    filename = re.sub(r'\s+', ' ', filename)
    
    # Loại bỏ khoảng trắng ở đầu và cuối
    filename = filename.strip()
    
    # Rút gọn nếu quá dài
    if len(filename) > max_length:
        filename = filename[:max_length].strip()
    
    # Nếu tên file rỗng, dùng tên mặc định
    if not filename:
        filename = "video"
    
    return filename


def sanitize_title(title):
    """
    Sanitize title từ video info để dùng làm tên file
    
    Args:
        title: Title của video
    
    Returns:
        Title đã được sanitize
    """
    return sanitize_filename(title, max_length=150)

