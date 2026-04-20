from flask import Flask, request, jsonify
import yt_dlp
import os
import re

app = Flask(__name__)

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
    return jsonify({'status': 'SnapFetch Server Running!', 'author': 'Ezzeldin'})

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
            # استخدام process=True و force_generic_extractor لو لزم الأمر لضمان سحب كل القصص
            info = ydl.extract_info(url, download=False, process=True)
            items = []
            seen_urls = set()

            # التأكد من وجود entries (سناب شات بروفايل بيرجع قائمة)
            entries = info.get('entries', [info])
            
            for entry in entries:
                if not entry: continue
                
                # أحياناً سناب شات بيرجع قائمة جوه قائمة، لازم نفكها
                nested_entries = entry.get('entries', [entry])
                
                for sub_entry in nested_entries:
                    # 1. تجاهل السبوتلايت تماماً
                    web_url = sub_entry.get('webpage_url', '').lower()
                    if 'spotlight' in web_url:
                        continue
                    
                    # 2. استخراج البيانات
                    item = extract_item_advanced(sub_entry)
                    
                    # 3. التأكد من عدم التكرار وأن الرابط موجود
                    if item and item['url'] not in seen_urls:
                        item['index'] = len(items) + 1
                        items.append(item)
                        seen_urls.add(item['url'])

            if not items:
                return jsonify({'error': 'No stories found'}), 404
                
            return jsonify({'items': items})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def clean_url(url):
    return url.strip()

def get_options(url):
    # استخدام صيغة مرنة جداً
    best_format = 'bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    base = {
        'quiet': True,
        'extract_flat': False,
        'format': best_format,
        'noplaylist': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        }
    }
    
    if 'snapchat.com' in url.lower():
        cookies = get_cookies_file('snapchat')
        if cookies:
            base['cookiefile'] = cookies
    # يمكنك إضافة باقي المنصات هنا بنفس الطريقة
    return base

def extract_item_advanced(info):
    """دالة متطورة للتفريق بين الصورة والفيديو في سناب شات"""
    try:
        # البحث عن أفضل رابط مباشر
        url_direct = info.get('url')
        formats = info.get('formats', [])
        
        if not url_direct and formats:
            url_direct = formats[-1].get('url')
        
        if not url_direct: return None

        # تحديد النوع بدقة (سناب شات أحياناً يضع vcodec=none للصور)
        vcodec = info.get('vcodec', 'none')
        ext = info.get('ext', '').lower()
        
        media_type = 'video'
        # إذا كان الامتداد صورة أو لا يوجد كوديك فيديو، نعتبرها صورة
        if ext in ['jpg', 'jpeg', 'png', 'webp'] or vcodec == 'none':
            media_type = 'image'
        
        # التأكد من الجودة
        height = info.get('height')
        quality = f"{height}p" if height else "High Quality"

        return {
            'url': url_direct,
            'title': info.get('title', 'Snapchat Story'),
            'type': media_type,
            'quality': quality,
            'thumbnail': info.get('thumbnail', ''),
            'duration': str(info.get('duration', '')) if media_type == 'video' else '',
            'ext': ext if ext else ('mp4' if media_type == 'video' else 'jpg')
        }
    except:
        return None

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
