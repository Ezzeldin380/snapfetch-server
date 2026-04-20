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
    return jsonify({'status': 'SnapFetch Server Ready', 'author': 'Ezzeldin'})

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url', '')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        ydl_opts = get_options(url)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج البيانات مع تفعيل المعالجة الكاملة لكل العناصر
            info = ydl.extract_info(url, download=False, process=True)
            items = []
            seen_ids = set() # لمنع التكرار نهائياً

            # التأكد من فك القوائم (Entries)
            raw_entries = []
            if 'entries' in info:
                # لو الرابط بروفايل أو بلايليست
                raw_entries = list(info['entries'])
            else:
                # لو فيديو واحد
                raw_entries = [info]

            for entry in raw_entries:
                if not entry: continue
                
                # أحياناً سناب شات بيرجع قائمة داخلية للقصص
                sub_elements = entry.get('entries', [entry])
                
                for sub in sub_elements:
                    if not sub: continue
                    
                    # 1. استبعاد السبوتلايت (Spotlight) بناءً على الرابط أو العنوان
                    webpage_url = sub.get('webpage_url', '').lower()
                    title = sub.get('title', '').lower()
                    if 'spotlight' in webpage_url or 'spotlight' in title:
                        continue
                    
                    # 2. تحديد المعرف الفريد لمنع التكرار (ID)
                    media_id = sub.get('id') or sub.get('url')
                    if media_id in seen_ids:
                        continue
                    
                    # 3. استخراج البيانات ومعالجة نوع الميديا (صورة أم فيديو)
                    item = process_entry(sub)
                    if item:
                        item['index'] = len(items) + 1
                        items.append(item)
                        seen_ids.add(media_id)

            if not items:
                return jsonify({'error': 'No stories found. Please check if stories are public.'}), 404
                
            return jsonify({'items': items})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_options(url):
    base = {
        'quiet': True,
        'extract_flat': False,
        'noplaylist': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        }
    }
    
    if 'snapchat.com' in url.lower():
        cookies = get_cookies_file('snapchat')
        if cookies:
            base['cookiefile'] = cookies
    # إضافة المنصات الأخرى هنا (فيسبوك، تيك توك.. إلخ)
    return base

def process_entry(info):
    """دالة متخصصة لفحص وتحليل بيانات السنابة"""
    try:
        # البحث عن الرابط المباشر في الـ formats أو الـ url
        direct_url = info.get('url')
        formats = info.get('formats', [])
        
        if not direct_url and formats:
            # نأخذ آخر فورمات لأنه غالباً يكون الأعلى جودة
            direct_url = formats[-1].get('url')
        
        if not direct_url: return None

        # --- تحديد النوع (فيديو أم صورة) ---
        # سناب شات للصور غالباً لا يضع vcodec أو يضعه none
        vcodec = info.get('vcodec', 'none')
        ext = info.get('ext', '').lower()
        
        media_type = 'video'
        # إذا كان الكوديك مفقود أو الامتداد يشير لصورة، نصنفها كصورة
        if vcodec == 'none' or ext in ['jpg', 'jpeg', 'png', 'webp']:
            media_type = 'image'
            # في الصور، أحياناً يكون الامتداد الفعلي هو jpg حتى لو مكتوب غير كدة
            if ext not in ['jpg', 'png', 'webp']: ext = 'jpg'
        
        return {
            'url': direct_url,
            'title': info.get('title', 'Snapchat Story'),
            'type': media_type,
            'quality': f"{info.get('height', 'HD')}p" if info.get('height') else "High Quality",
            'thumbnail': info.get('thumbnail', ''),
            'duration': str(info.get('duration', '')) if media_type == 'video' else '0',
            'ext': ext if ext else ('mp4' if media_type == 'video' else 'jpg')
        }
    except:
        return None

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
