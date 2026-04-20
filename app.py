from flask import Flask, request, jsonify
import yt_dlp
import os
import re

app = Flask(__name__)

# مسار مجلد الكوكيز
COOKIES_DIR = os.path.join(os.path.dirname(__file__), 'cookies')

def get_cookies_file(platform):
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
            info = ydl.extract_info(url, download=False, process=True)
            items = []
            seen_urls = set() # لمنع التكرار
            
            if 'entries' in info:
                entries = list(info['entries'])
                for entry in entries:
                    if not entry: continue
                    
                    # التعامل مع القصص المتداخلة
                    current_entries = entry.get('entries', [entry])
                    
                    for sub_entry in current_entries:
                        if not sub_entry: continue
                        
                        # 1. منع السبوتلايت (Spotlight)
                        # بنفحص العنوان أو الوصف أو الرابط لو فيه كلمة spotlight
                        title = sub_entry.get('title', '').lower()
                        entry_url = sub_entry.get('webpage_url', '').lower()
                        
                        if 'spotlight' in title or 'spotlight' in entry_url:
                            continue
                            
                        # 2. استخراج العنصر
                        item = extract_item(sub_entry, len(items) + 1)
                        
                        # 3. منع التكرار بناءً على الرابط المباشر
                        if item and item['url'] not in seen_urls:
                            items.append(item)
                            seen_urls.add(item['url'])
            else:
                item = extract_item(info, 1)
                if item: items.append(item)
            
            if not items:
                return jsonify({'error': 'No downloadable stories found (Spotlight excluded)'}), 404
                
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
        'extract_flat': False,
        'socket_timeout': 30,
        'format': best_format,
        'noplaylist': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        }
    }
    
    url_lower = url.lower()
    platform = None
    if 'tiktok.com' in url_lower: platform = 'tiktok'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower: platform = 'youtube'
    elif 'instagram.com' in url_lower: platform = 'instagram'
    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower: platform = 'facebook'
    elif 'snapchat.com' in url_lower: platform = 'snapchat'
    # ... باقي المنصات بنفس الطريقة

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

        return {
            'index': index,
            'url': url_direct,
            'title': info.get('title', f'Media_{index}'),
            'type': 'video', # الستوريز دائماً فيديو
            'quality': f"{info.get('height', 'HD')}p" if info.get('height') else 'High Quality',
            'thumbnail': info.get('thumbnail', ''),
            'duration': str(info.get('duration', '')),
            'ext': info.get('ext', 'mp4')
        }
    except Exception:
        return None

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
