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
        # إعدادات "جراحية" للوصول لعمق الداتا
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,  # جلب الروابط فقط في البداية لمنع التداخل
            'cookiefile': get_cookies_file('snapchat'),
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # الخطوة 1: سحب الميتا داتا الخام
            result = ydl.extract_info(url, download=False)
            
            # الخطوة 2: الدخول في كل الـ Entries المتاحة
            raw_entries = []
            if 'entries' in result:
                raw_entries = list(result['entries'])
            else:
                raw_entries = [result]

            items = []
            seen_media_urls = set() # الفلتر النهائي لمنع تكرار الميديا نفسها

            for entry in raw_entries:
                if not entry: continue
                
                # تجاهل السبوتلايت فوراً
                web_url = str(entry.get('url', '') or entry.get('webpage_url', '')).lower()
                if 'spotlight' in web_url:
                    continue

                # الخطوة 3: عمل Extract "حقيقي" لكل سنابة لوحدها لفك النوع والجودة
                try:
                    # هنا بنجبره يعمل ريفريش لكل عنصر عشان نتأكد هو صورة ولا فيديو
                    detail = ydl.extract_info(entry.get('url'), download=False, process=True)
                    
                    # جلب الرابط المباشر للميديا
                    media_url = detail.get('url') or (detail.get('formats')[-1]['url'] if detail.get('formats') else None)
                    
                    if not media_url or media_url in seen_media_urls:
                        continue
                    
                    # كشف النوع (صورة/فيديو) بناءً على غياب كوديك الفيديو
                    vcodec = detail.get('vcodec', 'none')
                    ext = detail.get('ext', '').lower()
                    is_image = vcodec == 'none' or ext in ['jpg', 'jpeg', 'png']

                    items.append({
                        'index': len(items) + 1,
                        'url': media_url,
                        'title': detail.get('title', 'Snap Story'),
                        'type': 'image' if is_image else 'video',
                        'quality': f"{detail.get('height', '1080')}p" if detail.get('height') else "HD",
                        'ext': 'jpg' if is_image else 'mp4',
                        'thumbnail': detail.get('thumbnail', ''),
                        'duration': str(detail.get('duration', '')) if not is_image else '0'
                    })
                    seen_media_urls.add(media_url)
                except:
                    continue # لو فشل في عنصر يكمل الباقي

            if not items:
                return jsonify({'error': 'No stories found.'}), 404
                
            return jsonify({'items': items})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
