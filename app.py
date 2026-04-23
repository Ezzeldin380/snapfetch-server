from flask import Flask, request, jsonify
import yt_dlp
import os
import re

app = Flask(__name__)

COOKIES_DIR = os.path.join(os.path.dirname(__file__), 'cookies')

def get_cookies_file(platform):
    if not os.path.exists(COOKIES_DIR):
        return None
    path = os.path.join(COOKIES_DIR, f'{platform}.txt')
    return path if os.path.exists(path) else None

@app.route('/')
def home():
    return jsonify({'status': 'SnapFetch Server Running!'})

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url', '')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    url = clean_url(url)

    try:
        ydl_opts = get_options(url)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            items = []
            index = 1

            if 'entries' in info and info['entries']:
                for entry in info['entries']:
                    if not entry:
                        continue
                    # تخطي Spotlight في Snapchat
                    entry_url = entry.get('url', '') or entry.get('webpage_url', '')
                    if 'spotlight' in entry_url.lower():
                        continue
                    item = extract_item(entry, index)
                    if item:
                        items.append(item)
                        index += 1
            else:
                item = extract_item(info, index)
                if item:
                    items.append(item)

            if not items:
                return jsonify({'error': 'No downloadable media found'}), 404

            return jsonify({'items': items})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def clean_url(url):
    url = url.strip()
    if 'soundcloud.com' in url:
        match = re.search(r'https?://(?:on\.)?soundcloud\.com/\S+', url)
        if match:
            return match.group(0)
    return url


def get_options(url):
    base = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'socket_timeout': 30,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        },
    }

    url_lower = url.lower()

    if 'snapchat.com' in url_lower:
        cookies = get_cookies_file('snapchat')
        base.update({'format': 'best'})
        if cookies:
            base['cookiefile'] = cookies

    elif 'tiktok.com' in url_lower:
        cookies = get_cookies_file('tiktok')
        base.update({'format': 'best[ext=mp4]/best'})
        if cookies:
            base['cookiefile'] = cookies

    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        cookies = get_cookies_file('youtube')
        if 'music.youtube.com' in url_lower:
            base.update({'format': 'bestaudio/best'})
        else:
            base.update({'format': 'best[ext=mp4]/best'})
        if cookies:
            base['cookiefile'] = cookies

    elif 'instagram.com' in url_lower:
        cookies = get_cookies_file('instagram')
        base.update({'format': 'best[ext=mp4]/best'})
        if cookies:
            base['cookiefile'] = cookies

    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower:
        cookies = get_cookies_file('facebook')
        base.update({'format': 'best[ext=mp4]/best'})
        if cookies:
            base['cookiefile'] = cookies

    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        cookies = get_cookies_file('twitter')
        base.update({'format': 'best'})
        if cookies:
            base['cookiefile'] = cookies

    elif 'reddit.com' in url_lower or 'redd.it' in url_lower:
        cookies = get_cookies_file('reddit')
        base.update({'format': 'best'})
        if cookies:
            base['cookiefile'] = cookies

    elif 'pinterest.com' in url_lower or 'pin.it' in url_lower:
        cookies = get_cookies_file('pinterest')
        base.update({'format': 'best'})
        if cookies:
            base['cookiefile'] = cookies

    elif 'kwai.com' in url_lower or 'kwai.me' in url_lower:
        cookies = get_cookies_file('kwai')
        base.update({
            'format': 'best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36',
                'Referer': 'https://www.kwai.com/',
            },
        })
        if cookies:
            base['cookiefile'] = cookies

    elif 'soundcloud.com' in url_lower:
        cookies = get_cookies_file('soundcloud')
        base.update({'format': 'bestaudio/best'})
        if cookies:
            base['cookiefile'] = cookies

    elif 'linkedin.com' in url_lower:
        base.update({'format': 'best'})

    elif 'threads.net' in url_lower:
        cookies = get_cookies_file('instagram')
        base.update({'format': 'best'})
        if cookies:
            base['cookiefile'] = cookies

    else:
        base.update({'format': 'best'})

    return base


def extract_item(info, index):
    try:
        formats = info.get('formats', [])
        url_direct = info.get('url', '')
        webpage_url = info.get('webpage_url', '')
        ext = info.get('ext', '')

        if ext in ['jpg', 'jpeg', 'png', 'webp']:
            return {
                'index': index,
                'url': url_direct or webpage_url,
                'type': 'image',
                'quality': 'Original',
                'thumbnail': info.get('thumbnail', ''),
                'duration': '',
            }

        if not formats and url_direct:
            media_type = 'audio' if ext in ['mp3', 'm4a', 'aac', 'opus'] else 'video'
            return {
                'index': index,
                'url': url_direct,
                'type': media_type,
                'quality': 'HD',
                'thumbnail': info.get('thumbnail', ''),
                'duration': str(info.get('duration', '')),
            }

        best_video = None
        best_audio = None

        for f in formats:
            if not f.get('url'):
                continue
            f_ext = f.get('ext', '')
            vcodec = f.get('vcodec', 'none')
            acodec = f.get('acodec', 'none')

            if f_ext in ['jpg', 'jpeg', 'png', 'webp']:
                return {
                    'index': index,
                    'url': f['url'],
                    'type': 'image',
                    'quality': 'Original',
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': '',
                }
            elif vcodec != 'none' and acodec != 'none':
                if best_video is None or (f.get('height', 0) or 0) > (best_video.get('height', 0) or 0):
                    best_video = f
            elif vcodec != 'none' and acodec == 'none':
                if best_video is None:
                    best_video = f
            elif vcodec == 'none' and acodec != 'none':
                if best_audio is None or (f.get('abr', 0) or 0) > (best_audio.get('abr', 0) or 0):
                    best_audio = f

        if best_video:
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
                'type': 'video',
                'quality': 'HD',
                'thumbnail': info.get('thumbnail', ''),
                'duration': str(info.get('duration', '')),
            }

        return None

    except Exception:
        return None


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
