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
    
    # تحويل رابط الـ Share لرابط بروفايل مباشر لو أمكن
    if 'add/' in url:
        username = url.split('add/')[1].split('?')[0]
        url = f"https://www.snapchat.com/add/{username}"

    try:
        # إعدادات إجبارية لجلب كل المحتوى (Scraping mode)
        ydl_opts = {
            'quiet': True,
            'extract_flat': True, 
            'force_generic_extractor': False,
            'cookiefile': get_cookies_file('snapchat'),
            'ignoreerrors': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج أولي للقائمة
            info = ydl.extract_info(url, download=False)
            
            if not info or 'entries' not in info:
                # محاولة تانية: لو فشل كـ Playlist جربه كـ Video فردي
                info = ydl.extract_info(url, download=False, process=True)

            items = []
            seen_ids = set()

            # التأكد من وجود داتا
            entries = info.get('entries', [info]) if info else []

            for entry in entries:
                if not entry: continue
                
                # 1. فلترة السبوتلايت الصارمة
                web_url = entry.get('url', '').lower() or entry.get('webpage_url', '').lower()
                title = entry.get('title', '').lower()
                if 'spotlight' in web_url or 'spotlight' in title:
                    continue

                # 2. منع التكرار (ID)
                entry_id = entry.get('id')
                if not entry_id or entry_id in seen_ids:
                    continue

                # 3. معالجة النوع (صورة/فيديو)
                # هنا بنعمل جلب للمعلومات الدقيقة للعنصر ده لوحده
                try:
                    # سحب بيانات السنابة الواحدة
                    sub_info = ydl.extract_info(entry.get('url'), download=False, process=True)
                    
                    vcodec = sub_info.get('vcodec', 'none')
                    ext = sub_info.get('ext', '').lower()
                    is_image = vcodec == 'none' or ext in ['jpg', 'jpeg', 'png']
                    
                    direct_url = sub_info.get('url') or (sub_info['formats'][-1]['url'] if sub_info.get('formats') else None)
                    
                    if direct_url:
                        items.append({
                            'index': len(items) + 1,
                            'url': direct_url,
                            'title': sub_info.get('title', 'Snap Story'),
                            'type': 'image' if is_image else 'video',
                            'quality': f"{sub_info.get('height', '1080')}p" if sub_info.get('height') else "HD",
                            'ext': 'jpg' if is_image else 'mp4',
                            'thumbnail': sub_info.get('thumbnail', ''),
                            'duration': str(sub_info.get('duration', '')) if not is_image else '0'
                        })
                        seen_ids.add(entry_id)
                except:
                    continue

            if not items:
                return jsonify({'error': 'No public stories found. Server might be blocked or cookies expired.'}), 404
                
            return jsonify({'items': items})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
