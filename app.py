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
    return jsonify({'status': 'SnapFetch Server Pro Running!', 'author': 'Ezzeldin'})

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url', '')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        ydl_opts = get_options(url)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج المعلومات - تم تفعيل process=True لإجبار السحب الكامل
            info = ydl.extract_info(url, download=False, process=True)
            
            items = []
            seen_urls = set() # لمنع التكرار نهائياً

            # سناب شات بروفايل بيرجع قائمة "entries"
            if 'entries' in info:
                entries = list(info['entries'])
            else:
                entries = [info]

            for entry in entries:
                if not entry: continue
                
                # أحياناً السنابات بتكون جوه entries فرعية
                sub_entries = entry.get('entries', [entry])
                for sub in sub_entries:
                    if not sub: continue
                    
                    # 1. فلترة السبوتلايت (Spotlight) الصارمة
                    web_url = sub.get('webpage_url', '').lower()
                    title = sub.get('title', '').lower()
                    if 'spotlight' in web_url or 'spotlight' in title:
                        continue
                    
                    # 2. معالجة البيانات والتفريق بين الصورة والفيديو
                    processed_item = process_snap_item(sub)
                    
                    # 3. التأكد من عدم التكرار (بناءً على رابط الميديا المباشر)
                    if processed_item and processed_item['url'] not in seen_urls:
                        processed_item['index'] = len(items) + 1
                        items.append(processed_item)
                        seen_urls.add(processed_item['url'])

            if not items:
                return jsonify({'error': 'No public stories found. Make sure the profile is public.'}), 404
                
            return jsonify({'items': items})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_options(url):
    # صيغة مرنة جداً لضمان عدم توقف السحب
    base = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'noplaylist': False,
        'socket_timeout': 30,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        }
    }
    
    if 'snapchat.com' in url.lower():
        cookies = get_cookies_file('snapchat')
        if cookies:
            base['cookiefile'] = cookies
            
    return base

def process_snap_item(info):
    """تحليل دقيق للسنابة للتفريق بين الصورة والفيديو"""
    try:
        # جلب الرابط المباشر
        direct_url = info.get('url')
        formats = info.get('formats', [])
        if not direct_url and formats:
            # نختار أفضل جودة فيديو/صورة متاحة
            direct_url = formats[-1].get('url')
        
        if not direct_url: return None

        # --- كشف نوع الميديا (صورة أم فيديو) ---
        vcodec = info.get('vcodec', 'none') # الكوديك الخاص بالفيديو
        ext = info.get('ext', '').lower()
        
        # في سناب شات: لو vcodec هو 'none' تبقى صورة 100%
        if vcodec == 'none' or ext in ['jpg', 'jpeg', 'png', 'webp']:
            media_type = 'image'
            actual_ext = ext if ext in ['jpg', 'png', 'webp'] else 'jpg'
        else:
            media_type = 'video'
            actual_ext = 'mp4'

        return {
            'url': direct_url,
            'title': info.get('title', 'Snapchat Story'),
            'type': media_type,
            'quality': f"{info.get('height', '1080')}p" if info.get('height') else "High Quality",
            'thumbnail': info.get('thumbnail', ''),
            'duration': str(info.get('duration', '')) if media_type == 'video' else '0',
            'ext': actual_ext
        }
    except:
        return None

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
