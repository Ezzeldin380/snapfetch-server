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
        # إعدادات لكسر حماية سناب شات وجلب القائمة كاملة
        ydl_opts = {
            'quiet': True,
            'extract_flat': 'in_playlist', # يجيب الروابط الأول عشان نتحكم فيها
            'cookiefile': get_cookies_file('snapchat'),
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # الخطوة 1: سحب "خريطة" الحساب
            info = ydl.extract_info(url, download=False)
            
            if 'entries' not in info:
                return jsonify({'error': 'Could not find stories list. Ensure the profile is public.'}), 404

            items = []
            seen_media_ids = set()

            # الخطوة 2: المرور على كل "سنابة" بشكل منفصل
            for entry in info['entries']:
                if not entry: continue
                
                entry_url = entry.get('url', '')
                
                # 1. فلترة السبوتلايت (Spotlight) فوراً
                if 'spotlight' in entry_url.lower():
                    continue
                
                # 2. جلب بيانات السنابة الواحدة بدقة
                try:
                    # بنطلب منه يعيد فحص الرابط ده بالذات عشان نعرف هو صورة ولا فيديو
                    snap_detail = ydl.extract_info(entry_url, download=False, process=True)
                    
                    # منع التكرار بناءً على الـ ID الحقيقي للميديا
                    snap_id = snap_detail.get('id')
                    if snap_id in seen_media_ids: continue

                    # 3. تحديد النوع (صورة أم فيديو)
                    # سناب شات للصور لا يضع vcodec أو يضع 'none'
                    vcodec = snap_detail.get('vcodec', 'none')
                    ext = snap_detail.get('ext', '').lower()
                    is_image = (vcodec == 'none' or ext in ['jpg', 'jpeg', 'png'])

                    # جلب الرابط المباشر
                    direct_url = snap_detail.get('url') or (snap_detail['formats'][-1]['url'] if snap_detail.get('formats') else None)

                    if direct_url:
                        items.append({
                            'index': len(items) + 1,
                            'url': direct_url,
                            'title': snap_detail.get('title', 'Snap Story'),
                            'type': 'image' if is_image else 'video',
                            'quality': f"{snap_detail.get('height', '1080')}p" if snap_detail.get('height') else "HD",
                            'ext': 'jpg' if is_image else 'mp4',
                            'thumbnail': snap_detail.get('thumbnail', ''),
                            'duration': str(snap_detail.get('duration', '')) if not is_image else '0'
                        })
                        seen_media_ids.add(snap_id)
                        
                        # اختياري: لو عايز توقف عند أول 20 ستوري بس
                        if len(items) >= 20: break
                except:
                    continue

            if not items:
                return jsonify({'error': 'No public stories extracted.'}), 404
                
            return jsonify({'items': items})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
