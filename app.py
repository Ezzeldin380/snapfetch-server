from flask import Flask, request, jsonify
import yt_dlp
import os
import re

app = Flask(__name__)

COOKIES_DIR = os.path.join(os.path.dirname(__file__), 'cookies')

def get_cookies_file(platform):
    if not os.path.exists(COOKIES_DIR): return None
    for filename in os.listdir(COOKIES_DIR):
        if platform in filename.lower() and filename.endswith('.txt'):
            return os.path.join(COOKIES_DIR, filename)
    return None

@app.route('/')
def home():
    return jsonify({'status': 'SnapFetch Pro Running', 'author': 'Ezzeldin'})

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url', '')
    if not url: return jsonify({'error': 'No URL provided'}), 400
    
    try:
        # إعدادات خاصة لإجبار سناب شات على كشف كل المحتوى
        ydl_opts = {
            'quiet': True,
            'extract_flat': False, # لازم False عشان يفتح كل قصة
            'force_generic_extractor': False,
            'noplaylist': False,
            'playlist_items': '1:50', # إجبار السحب لـ 50 عنصر لو موجودين
            'cookiefile': get_cookies_file('snapchat'),
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج المعلومات مع معالجة كاملة
            info = ydl.extract_info(url, download=False, process=True)
            
            items = []
            seen_ids = set() # لمنع تكرار أول قصة والسبوتلايت

            # فك الطبقات (سناب شات أحياناً يضع القصص في 'entries')
            all_entries = []
            if 'entries' in info:
                all_entries = list(info['entries'])
            else:
                all_entries = [info]

            for entry in all_entries:
                if not entry: continue
                
                # الدخول في العمق (Nested Entries)
                sub_elements = entry.get('entries', [entry])
                for sub in sub_elements:
                    if not sub: continue
                    
                    # 1. منع السبوتلايت (Spotlight) نهائياً
                    web_url = sub.get('webpage_url', '').lower()
                    if 'spotlight' in web_url: continue
                    
                    # 2. منع التكرار بناءً على الـ ID الفريد للسنابة
                    snap_id = sub.get('id')
                    if snap_id in seen_ids: continue
                    
                    # 3. تحليل الميديا (صورة أم فيديو)
                    item = process_snap(sub)
                    if item:
                        item['index'] = len(items) + 1
                        items.append(item)
                        seen_ids.add(snap_id)

            if not items:
                return jsonify({'error': 'No stories found. Check profile privacy.'}), 404
                
            return jsonify({'items': items})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_snap(info):
    try:
        # جلب الرابط المباشر
        direct_url = info.get('url')
        if not direct_url and info.get('formats'):
            direct_url = info['formats'][-1].get('url')
        
        if not direct_url: return None

        # كشف الصور: سناب شات يضع vcodec='none' للصور
        vcodec = info.get('vcodec', 'none')
        ext = info.get('ext', 'mp4').lower()
        
        is_image = vcodec == 'none' or ext in ['jpg', 'jpeg', 'png', 'webp']
        
        return {
            'url': direct_url,
            'title': info.get('title', 'Snap Story'),
            'type': 'image' if is_image else 'video',
            'quality': f"{info.get('height', '1080')}p" if info.get('height') else "High Quality",
            'ext': 'jpg' if is_image else 'mp4',
            'thumbnail': info.get('thumbnail', ''),
            'duration': str(info.get('duration', '')) if not is_image else '0'
        }
    except: return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
