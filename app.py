from flask import Flask, request, jsonify
import yt_dlp
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'status': 'SnapFetch Server Running!'})

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url', '')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        # إعدادات مختلفة حسب المنصة
        ydl_opts = _get_options(url)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            items = []
            index = 1
            
            if 'entries' in info and info['entries']:
                for entry in info['entries']:
                    if entry:
                        item = _extract_item(entry, index)
                        if item:
                            items.append(item)
                            index += 1
            else:
                item = _extract_item(info, index)
                if item:
                    items.append(item)
            
            return jsonify({'items': items})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _get_options(url):
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    url_lower = url.lower()
    
    # Snapchat
    if 'snapchat.com' in url_lower:
        base_opts.update({
            'extractor_args': {'snapchat': {'stories': True}},
        })
    
    # Instagram Stories
    elif 'instagram.com/stories' in url_lower:
        base_opts.update({
            'cookiesfrombrowser': None,
        })
    
    # Facebook
    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower:
        base_opts.update({
            'format': 'best',
        })
    
    # Pinterest
    elif 'pinterest.com' in url_lower or 'pin.it' in url_lower:
        base_opts.update({
            'format': 'best',
        })
    
    # Reddit
    elif 'reddit.com' in url_lower or 'redd.it' in url_lower:
        base_opts.update({
            'format': 'best',
        })
    
    # Kwai
    elif 'kwai.com' in url_lower:
        base_opts.update({
            'format': 'best',
        })
    
    return base_opts

def _extract_item(info, index):
    try:
        formats = info.get('formats', [])
        url_direct = info.get('url', '')
        
        # لو مفيش formats خد الـ url مباشرة
        if not formats and url_direct:
            return {
                'index': index,
                'url': url_direct,
                'type': _get_type(info),
                'quality': 'HD',
                'thumbnail': info.get('thumbnail', ''),
                'duration': str(info.get('duration', '')),
            }
        
        best_video = None
        best_audio = None
        best_image = None
        
        for f in formats:
            ext = f.get('ext', '')
            vcodec = f.get('vcodec', 'none')
            acodec = f.get('acodec', 'none')
            
            # صورة
            if ext in ['jpg', 'jpeg', 'png', 'webp']:
                best_image = f
            # فيديو مع صوت
            elif vcodec != 'none' and acodec != 'none':
                if best_video is None or (f.get('height', 0) or 0) > (best_video.get('height', 0) or 0):
                    best_video = f
            # صوت فقط
            elif vcodec == 'none' and acodec != 'none':
                if best_audio is None or (f.get('abr', 0) or 0) > (best_audio.get('abr', 0) or 0):
                    best_audio = f
        
        # اختار الأفضل
        if best_image:
            return {
                'index': index,
                'url': best_image['url'],
                'type': 'image',
                'quality': 'Original',
                'thumbnail': info.get('thumbnail', ''),
                'duration': '',
            }
        elif best_video:
            height = best_video.get('height', 0) or 0
            return {
                'index': index,
                'url': best_video['url'],
                'type': 'video',
                'quality': f'{height}p' if height else 'HD',
                'thumbnail': info.get('thumbnail', ''),
                'duration': str(info.get('duration', '')),
            }
        elif best_audio:
            return {
                'index': index,
                'url': best_audio['url'],
                'type': 'audio',
                'quality': f"{best_audio.get('abr', 'HD')}kbps",
                'thumbnail': info.get('thumbnail', ''),
                'duration': str(info.get('duration', '')),
            }
        elif url_direct:
            return {
                'index': index,
                'url': url_direct,
                'type': _get_type(info),
                'quality': 'HD',
                'thumbnail': info.get('thumbnail', ''),
                'duration': str(info.get('duration', '')),
            }
        
        return None
        
    except Exception as e:
        return None

def _get_type(info):
    ext = info.get('ext', '')
    if ext in ['jpg', 'jpeg', 'png', 'webp']:
        return 'image'
    elif ext in ['mp3', 'aac', 'm4a', 'opus']:
        return 'audio'
    return 'video'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
