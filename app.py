#!/usr/bin/env python3
"""
Flask web application để download video từ các nền tảng
"""

from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import os
import tempfile
import atexit
from youtube import download_youtube
from tiktok import download_tiktok
from instagram import download_instagram
from facebook import download_facebook

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Thư mục tạm để lưu video trước khi gửi cho user
TEMP_DIR = tempfile.mkdtemp(prefix='video_downloader_')

# Danh sách file tạm cần xóa
temp_files = []


def cleanup_temp_files():
    """Xóa các file tạm khi server tắt"""
    import shutil
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR, ignore_errors=True)


atexit.register(cleanup_temp_files)


@app.route('/')
def index():
    """Trang chủ với form download"""
    return render_template('index.html')


@app.route('/download', methods=['POST'])
def download():
    """API endpoint để xử lý download video và trả về file cho user"""
    try:
        data = request.get_json()
        platform = data.get('platform', '').lower()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'success': False, 'message': 'Vui lòng nhập URL video'}), 400
        
        if not platform:
            return jsonify({'success': False, 'message': 'Vui lòng chọn nền tảng'}), 400
        
        # Tạo thư mục tạm nếu chưa có
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
        
        # Download video vào thư mục tạm
        try:
            if platform == 'youtube':
                file_path = download_youtube(url, TEMP_DIR)
            elif platform == 'tiktok':
                file_path = download_tiktok(url, TEMP_DIR)
            elif platform == 'instagram':
                file_path = download_instagram(url, TEMP_DIR)
            elif platform == 'facebook':
                file_path = download_facebook(url, TEMP_DIR)
            else:
                return jsonify({'success': False, 'message': f'Platform không được hỗ trợ: {platform}'}), 400
            
            if not file_path or not os.path.exists(file_path):
                return jsonify({'success': False, 'message': 'Không thể download video'}), 500
            
            # Lấy tên file
            filename = os.path.basename(file_path)
            
            # Đăng ký xóa file sau khi gửi xong
            @after_this_request
            def remove_file(response):
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Lỗi khi xóa file tạm: {e}")
                return response
            
            # Trả về file cho user download
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='video/mp4'
            )
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'Lỗi khi download video: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8880)

