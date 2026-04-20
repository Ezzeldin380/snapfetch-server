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
        # إعدادات مخصصة لكسر حماية سناب شات وجلب القائمة كاملة
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,      # إجبار المكتبة على الدخول لكل رابط فرعي
            'lazy_playlist': False,     # سحب القائمة كاملة فوراً
            'noplaylist': False,        # السماح بالقوائم
            'cookiefile': get_cookies_file('snapchat'),
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # هنا بنعمل جلب كامل للبيانات والمعالجة
            info = ydl.extract_info(url, download=False, process=True)
            
            items = []
            seen_ids = set()

            # لو النتيجة قائمة (وده اللي بيحصل مع روابط البروفايل أو الـ Share)
            if 'entries' in info:
                raw_entries = info['entries']
            else:
                raw_entries = [info]

            for entry in raw_entries:
                if not entry: continue
                
                # أحياناً سناب شات بيحط الستوريز في طبقة تانية
                sub_entries = entry.get('entries', [entry])
                
                for sub in sub_entries:
                    if not sub: continue
                    
                    # 1. فلترة السبوتلايت (Spotlight) بالاسم والرابط
                    webpage_url = sub.get('webpage_url', '').lower()
                    title = sub.get('title', '').lower()
                    if 'spotlight' in webpage_url or 'spotlight' in title:
                        continue
                    
                    # 2. منع التكرار بناءً على الـ ID الفريد
                    snap_id = sub.get('id')
                    if not snap_id or snap_id in seen_ids:
                        continue
                    
                    # 3. استخراج البيانات مع التفريق بين الصورة والفيديو
                    # السر في نوع الميديا هو الـ vcodec والـ ext
                    vcodec = sub.get('vcodec', 'none')
                    ext = sub.get('ext', '').lower()
                    
                    # إذا لم يوجد كوديك فيديو، فهي صورة بنسبة 100%
                    is_image = vcodec == 'none' or ext in ['jpg', 'jpeg', 'png', 'webp']
                    
                    # جلب الرابط المباشر (Direct URL)
                    direct_url = sub.get('url') or (sub.get('formats')[-1]['url'] if sub.get('formats') else None)
                    
                    if direct_url:
                        items.append({
                            'index': len(items) + 1,
                            'url': direct_url,
                            'title': sub.get('title', 'Snap Story'),
                            'type': 'image' if is_image else 'video',
                            'quality': f"{sub.get('height', '1080')}p" if sub.get('height') else "High Quality",
                            'ext': 'jpg' if is_image else 'mp4',
                            'thumbnail': sub.get('thumbnail', ''),
                            'duration': str(sub.get('duration', '')) if not is_image else '0'
                        })
                        seen_ids.add(snap_id)

            if not items:
                return jsonify({'error': 'No stories found. Check privacy.'}), 404
                
            return jsonify({'items': items})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
