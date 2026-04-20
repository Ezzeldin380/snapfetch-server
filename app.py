from flask import Flask, request, jsonify
import yt_dlp
import os
import re

app = Flask(__name__)

# مسار مجلد الكوكيز
COOKIES_DIR = os.path.join(os.path.dirname(__file__), 'cookies')

def get_cookies_file(platform):
    """دالة ذكية للبحث عن ملف الكوكيز الخاص بالمنصة"""
    if not os.path.exists(COOKIES_DIR):
        return None
    
    for filename in os.listdir(COOKIES_DIR):
        if platform in filename.lower() and filename.endswith('.txt'):
            return os.path.join(COOKIES_DIR, filename)
    return None

@app.route('/')
def home():
    return jsonify({'status': 'SnapFetch Server is Running!', 'author': 'Ezzeldin'})

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url', '')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    url = clean_url(url)
    
    try:
        ydl_opts = get_options(url)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # تم إضافة process=True لضمان استخراج كافة العناصر داخل القائمة (مثل قصص سناب شات)
            info = ydl.extract_info(url, download=False, process=True)
            items = []
            
            # فحص ما إذا كانت النتيجة قائمة فيديوهات (Playlist/Stories)
            if 'entries' in info:
                entries = list(info['entries'])
                for index, entry in enumerate(entries, start=1):
                    if entry:
                        # التعامل مع القصص المتداخلة إذا وجدت
                        if 'entries' in entry:
                            for sub_entry in entry['entries']:
                                item = extract_item(sub_entry, len(items) + 1)
                                if item: items.append(item)
                        else:
                            item = extract_item(entry, len(items) + 1)
                            if item: items.append(item)
            else:
                # فيديو واحد فقط
                item = extract_item(info, 1)
                if item: items.append(item)
            
            if not items:
                return jsonify({'error': 'No downloadable media found'}), 404
                
            return jsonify({'items': items})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def clean_url(url):
    url = url.strip()
    if 'soundcloud.com' in url:
        match = re.search(r'https?://(?:on\.)?soundcloud\.com/\S+', url)
        if match: return match.group(0)
    return url

def get_options(url):
    best_format = 'bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    
    base = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False, # يجب أن تكون False لجلب محتوى القصص
        'socket_timeout': 30,
        'format': best_format,
        'noplaylist': False, # السماح بجلب قوائم التشغيل والقصص المتعددة
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        }
    }
    
    url_lower = url.lower()
    platform = None
    if 'tiktok.com' in url_lower: platform = 'tiktok'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        if 'music.youtube.com' in url_lower: base['format'] = 'bestaudio/best'
        platform = 'youtube'
    elif 'instagram.com' in url_lower: platform = 'instagram'
    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower: platform = 'facebook'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower: platform = 'twitter'
    elif 'reddit.com' in url_lower or 'redd.it' in url_lower: platform = 'reddit'
    elif 'pinterest.com' in url_lower or 'pin.it' in url_lower: platform = 'pinterest'
    elif 'snapchat.com' in url_lower: platform = 'snapchat'
    elif 'kwai.com' in url_lower or 'kwai.me' in url_lower: platform = 'kwai'
    elif 'soundcloud.com' in url_lower: 
        platform = 'soundcloud'
        base['format'] = 'bestaudio/best'
    elif 'threads.net' in url_lower: platform = 'instagram'

    if platform:
        cookies = get_cookies_file(platform)
        if cookies:
            base['cookiefile'] = cookies

    return base

def extract_item(info, index):
    try:
        url_direct = info.get('url')
        formats = info.get('formats', [])
        
        if not url_direct and formats:
            valid_formats = [f for f in formats if f.get('url')]
            if valid_formats:
                url_direct = valid_formats[-1]['url']
        
        if not url_direct: return None

        ext = info.get('ext', 'mp4')
        media_type = 'video'
        
        if ext in ['jpg', 'jpeg', 'png', 'webp']:
            media_type = 'image'
        elif ext in ['mp3', 'm4a', 'aac', 'opus'] or 'audio' in info.get('format', '').lower():
            media_type = 'audio'

        return {
            'index': index,
            'url': url_direct,
            'title': info.get('title', f'Media_{index}'),
            'type': media_type,
            'quality': f"{info.get('height', 'HD')}p" if info.get('height') else 'High Quality',
            'thumbnail': info.get('thumbnail', ''),
            'duration': str(info.get('duration', '')),
            'ext': ext
        }
    except Exception:
        return None

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
