from flask import Flask, request, jsonify
import yt_dlp
import os

app = Flask(__name__)

COOKIES_DIR = os.path.join(os.path.dirname(__file__), 'cookies')

def get_cookies_file(platform):
    if not os.path.exists(COOKIES_DIR): return None
    for filename in os.listdir(COOKIES_DIR):
        if platform in filename.lower() and filename.endswith('.txt'):
            return os.path.join(COOKIES_DIR, filename)
    return None

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url', '')
    if not url: return jsonify({'error': 'No URL provided'}), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': 'in_playlist', # السر هنا: يجيب القائمة كاملة من غير معالجة سطحية
            'cookiefile': get_cookies_file('snapchat'),
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # سحب البيانات الخام
            info = ydl.extract_info(url, download=False)
            
            raw_items = []
            if 'entries' in info:
                raw_items = list(info['entries'])
            else:
                raw_items = [info]

            final_items = []
            seen_ids = set() # فلتر لمنع التكرار نهائياً

            for entry in raw_items:
                if not entry: continue
                
                # 1. فلترة السبوت لايت (Spotlight) الصارمة
                # أي عنصر مكتوب فيه spotlight في الـ ID أو الرابط أو العنوان يتم حذفه
                entry_id = str(entry.get('id', ''))
                web_url = str(entry.get('url', '') or entry.get('webpage_url', '')).lower()
                title = str(entry.get('title', '')).lower()
                
                if 'spotlight' in web_url or 'spotlight' in title or 'spotlight' in entry_id:
                    continue

                # 2. منع التكرار (بناءً على الـ ID الفريد)
                if entry_id in seen_ids:
                    continue

                # 3. تحليل نوع الميديا (صورة أم فيديو)
                # في سناب شات: الصور دايماً vcodec بتاعها بيكون none
                vcodec = entry.get('vcodec', 'none')
                ext = entry.get('ext', '').lower()
                
                is_image = (vcodec == 'none' or ext in ['jpg', 'jpeg', 'png', 'webp'])
                
                # 4. بناء الكائن النهائي
                item = {
                    'index': len(final_items) + 1,
                    'url': entry.get('url') or entry.get('webpage_url'),
                    'title': entry.get('title', 'Snap Story'),
                    'type': 'image' if is_image else 'video',
                    'quality': f"{entry.get('height', '1080')}p" if entry.get('height') else "High Quality",
                    'ext': 'jpg' if is_image else 'mp4',
                    'thumbnail': entry.get('thumbnail', ''),
                    'duration': str(entry.get('duration', '')) if not is_image else '0'
                }
                
                if item['url']:
                    final_items.append(item)
                    seen_ids.add(entry_id)

            if not final_items:
                return jsonify({'error': 'No public stories found.'}), 404
                
            return jsonify({'items': final_items})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
