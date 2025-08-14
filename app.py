from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import json
import re
import tempfile
import random
import time

app = Flask(__name__)
CORS(app)

# רשימת User-Agents למימוש דפדפנים שונים
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
]

def extract_video_id(url):
    """חילוץ מזהה סרטון מ-URL או החזרת המזהה אם כבר קיים"""
    if len(url) == 11 and not '/' in url:
        return url
    
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return url

def get_video_info(video_input, attempt=1):
    """קבלת מידע על סרטון עם מספר ניסיונות וגישות שונות"""
    video_id = extract_video_id(video_input)
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # בחירת User-Agent אקראי
    user_agent = random.choice(USER_AGENTS)
    
    # הגדרות שונות לכל ניסיון
    if attempt == 1:
        # ניסיון ראשון - הגדרות בסיסיות משופרות
        ydl_opts = {
            'format': 'best[height<=720][ext=mp4]/best[height<=480][ext=mp4]/best[ext=mp4]/best',
            'no_warnings': True,
            'quiet': True,
            'no_color': True,
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
            'ignoreerrors': False,
            'http_headers': {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            },
            'extractor_args': {
                'youtube': {
                    'skip': ['hls', 'dash'],
                    'player_client': ['android', 'web']
                }
            }
        }
    elif attempt == 2:
        # ניסיון שני - עם Android client
        ydl_opts = {
            'format': 'best[height<=720]/best[height<=480]/best',
            'no_warnings': True,
            'quiet': True,
            'no_color': True,
            'http_headers': {
                'User-Agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; SM-G973F) gzip'
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']
                }
            }
        }
    else:
        # ניסיון שלישי - עם iOS client
        ydl_opts = {
            'format': 'best[height<=720]/best[height<=480]/best',
            'no_warnings': True,
            'quiet': True,
            'no_color': True,
            'http_headers': {
                'User-Agent': 'com.google.ios.youtube/17.33.2 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)'
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios']
                }
            }
        }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Attempt {attempt}: Trying to extract info for {video_id}")
            info = ydl.extract_info(url, download=False)
            
            # מחפש את הפורמט הטוב ביותר
            formats = info.get('formats', [])
            best_format = None
            
            # מעדיף פורמטים משולבים (וידאו + אודיו)
            for fmt in formats:
                if (fmt.get('vcodec') != 'none' and 
                    fmt.get('acodec') != 'none' and 
                    fmt.get('url')):
                    best_format = fmt
                    break
            
            # אם לא מצא משולב, לוקח וידאו בלבד
            if not best_format:
                for fmt in formats:
                    if fmt.get('vcodec') != 'none' and fmt.get('url'):
                        best_format = fmt
                        break
            
            # אם עדיין לא מצא, לוקח כל פורמט זמין
            if not best_format and formats:
                best_format = formats[0]
            
            if not best_format:
                return {
                    'success': False,
                    'error': 'No suitable format found'
                }
            
            print(f"Success on attempt {attempt}")
            return {
                'success': True,
                'video_id': video_id,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'download_url': best_format.get('url', ''),
                'format_note': best_format.get('format_note', 'Unknown'),
                'ext': best_format.get('ext', 'mp4'),
                'filesize': best_format.get('filesize'),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', ''),
                'attempt_used': attempt
            }
            
    except Exception as e:
        error_msg = str(e)
        print(f"Attempt {attempt} failed: {error_msg}")
        
        # אם זה לא הניסיון האחרון, נסה שוב
        if attempt < 3:
            print(f"Retrying with attempt {attempt + 1}")
            time.sleep(1)  # המתנה קצרה בין ניסיונות
            return get_video_info(video_input, attempt + 1)
        
        return {
            'success': False,
            'error': error_msg,
            'video_id': video_id,
            'attempts_made': 3
        }

@app.route('/')
def home():
    return jsonify({
        'status': 'active',
        'service': 'Enhanced yt-dlp API Server',
        'version': '2.0',
        'features': [
            'Multiple User-Agent rotation',
            'Android/iOS client emulation', 
            'Multiple retry attempts',
            'Anti-blocking measures'
        ],
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
        
        print(f"Processing download request for: {video_input}")
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
                    'thumbnail': result['thumbnail'],
                    'attempt_used': result.get('attempt_used', 1)
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'attempts_made': result.get('attempts_made', 1)
            }), 400
            
    except Exception as e:
        print(f"Server error: {str(e)}")
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
        
        print(f"Processing info request for: {video_input}")
        result = get_video_info(video_input)
        return jsonify(result)
        
    except Exception as e:
        print(f"Server error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/test', methods=['GET'])
def test():
    """נקודת בדיקה עם סרטון קבוע"""
    test_video = "jNQXAC9IVRw"  # Me at the zoo - הסרטון הראשון ב-YouTube
    result = get_video_info(test_video)
    return jsonify({
        'test_video': test_video,
        'result': result
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
