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
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            items = []
            index = 1
            
            # لو playlist أو stories
            if 'entries' in info:
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

def _extract_item(info, index):
    try:
        # الفيديو الأفضل جودة
        formats = info.get('formats', [])
        
        best_video = None
        best_audio = None
        
        for f in formats:
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                if best_video is None or (f.get('height', 0) or 0) > (best_video.get('height', 0) or 0):
                    best_video = f
            elif f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                if best_audio is None or (f.get('abr', 0) or 0) > (best_audio.get('abr', 0) or 0):
                    best_audio = f
        
        items = []
        
        if best_video:
            items.append({
                'index': index,
                'url': best_video['url'],
                'type': 'video',
                'quality': f"{best_video.get('height', 'HD')}p",
                'thumbnail': info.get('thumbnail', ''),
                'duration': str(info.get('duration', '')),
            })
        
        if best_audio and not best_video:
            items.append({
                'index': index,
                'url': best_audio['url'],
                'type': 'audio',
                'quality': f"{best_audio.get('abr', 'HD')}kbps",
                'thumbnail': info.get('thumbnail', ''),
                'duration': str(info.get('duration', '')),
            })
        
        return items[0] if items else None
        
    except Exception as e:
        return None

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
