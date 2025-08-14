from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import json
import re

app = Flask(__name__)
CORS(app)  # מאפשר קריאות מ-Google Apps Script

def extract_video_id(url):
    """חילוץ מזהה סרטון מ-URL או החזרת המזהה אם כבר קיים"""
    if len(url) == 11 and not '/' in url:  # כנראה מזהה ישיר
        return url
    
    # דפוסים שונים של YouTube URLs
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return url  # אם לא מצאנו תבנית, נחזיר כמו שזה

def get_video_info(video_input):
    """קבלת מידע על סרטון"""
    video_id = extract_video_id(video_input)
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    ydl_opts = {
    'format': 'best[height<=720]/best[height<=480]/best',
    'no_warnings': True,
    'extractaudio': False,
    'quiet': True,
    'no_color': True,
    # הוספת כותרות לחיקוי דפדפן רגיל
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    },
        # נסה עם הגדרות שונות אם הראשונה נכשלת
        'retries': 3,
        'fragment_retries': 3,
        'extractor_retries': 3,
}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # מחפש את הפורמט הטוב ביותר
            formats = info.get('formats', [])
            best_format = None
            
            for fmt in formats:
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    best_format = fmt
                    break
            
            if not best_format and formats:
                best_format = formats[-1]  # לוקח את האחרון אם לא מצא משולב
            
            return {
                'success': True,
                'video_id': video_id,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'download_url': best_format.get('url', '') if best_format else '',
                'format_note': best_format.get('format_note', 'Unknown') if best_format else '',
                'ext': best_format.get('ext', 'mp4') if best_format else 'mp4',
                'filesize': best_format.get('filesize') if best_format else None,
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', '')
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'video_id': video_id
        }

@app.route('/')
def home():
    return jsonify({
        'status': 'active',
        'service': 'yt-dlp API Server',
        'version': '1.0',
        'endpoints': {
            'POST /download': 'Get download URL for video',
            'POST /info': 'Get video information',
            'GET /': 'This status page'
        },
        'usage': {
            'method': 'POST',
            'content-type': 'application/json',
            'body': '{"video": "VIDEO_ID_OR_URL"}'
        }
    })

@app.route('/download', methods=['POST', 'GET'])
def download():
    if request.method == 'GET':
        return jsonify({'error': 'Use POST method with JSON body containing "video" field'}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400
            
        video_input = data.get('video', '').strip()
        if not video_input:
            return jsonify({'error': 'Missing "video" parameter'}), 400
        
        result = get_video_info(video_input)
        
        if result['success']:
            return jsonify({
                'success': True,
                'download_url': result['download_url'],
                'video_info': {
                    'title': result['title'],
                    'duration': result['duration'],
                    'format': result['format_note'],
                    'ext': result['ext'],
                    'thumbnail': result['thumbnail']
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/info', methods=['POST'])
def info():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400
            
        video_input = data.get('video', '').strip()
        if not video_input:
            return jsonify({'error': 'Missing "video" parameter'}), 400
        
        result = get_video_info(video_input)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    app.run(host='0.0.0.0', port=port, debug=False)

