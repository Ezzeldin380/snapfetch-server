from flask import Flask, request, jsonify
import yt_dlp
import os
import subprocess
import sys

# تحديث المكتبة عند بدء التشغيل
try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
except Exception as e:
    print(f"Update failed: {e}")

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
            'extract_flat': 'in_playlist',
            'cookiefile': get_cookies_file('snapchat'),
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. سحب خريطة الحساب (بدون معالجة كاملة في البداية لسرعة جلب القائمة)
            info = ydl.extract_info(url, download=False)
            
            # التأكد من وجود قصص
            raw_entries = info.get('entries', [])
            if not raw_entries and 'url' in info:
                raw_entries = [info] # حالة لو الرابط لسنابة واحدة فقط
            
            if not raw_entries:
                return jsonify({'error': 'No stories found in this account.'}), 404

            items = []
            seen_media_ids = set()

            # 2. اللوب على كل القصص المتاحة (بدون ليميت)
            for entry in raw_entries:
                if not entry: continue
                
                entry_url = entry.get('url') or entry.get('webpage_url')
                if not entry_url: continue
                
                # فلترة السبوتلايت فوراً قبل الدخول في التفاصيل
                if 'spotlight' in entry_url.lower(): continue
                
                try:
                    # فحص تفصيلي لكل سنابة
                    snap_detail = ydl.extract_info(entry_url, download=False, process=True)
                    
                    snap_id = snap_detail.get('id')
                    if not snap_id or snap_id in seen_media_ids: continue

                    # تحديد النوع (صورة/فيديو)
                    vcodec = snap_detail.get('vcodec', 'none')
                    ext = snap_detail.get('ext', '').lower()
                    is_image = (vcodec == 'none' or any(x in ext for x in ['jpg', 'jpeg', 'png', 'webp']))

                    direct_url = snap_detail.get('url')
                    if not direct_url and snap_detail.get('formats'):
                        direct_url = snap_detail['formats'][-1].get('url')

                    if direct_url:
                        items.append({
                            'index': len(items) + 1,
                            'url': direct_url,
                            'title': snap_detail.get('title', 'Snap Story'),
                            'type': 'image' if is_image else 'video',
                            'quality': f"{snap_detail.get('height', '1080')}p" if snap_detail.get('height') else "HD",
                            'ext': 'jpg' if is_image else 'mp4',
                            'thumbnail': snap_detail.get('thumbnail', ''),
                            'duration': str(snap_detail.get('duration', '0')) if not is_image else '0'
                        })
                        seen_media_ids.add(snap_id)
                except:
                    # لو سنابة فيها مشكلة (مثلاً اتمسحت وقت السحب) يتخطاها ويكمل الباقي
                    continue

            return jsonify({
                'total_found': len(items),
                'items': items
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # تشغيل السيرفر على بورت 8080 (أو حسب إعدادات السيرفر)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
