"""
Módulo para resolución y obtención de URLs de streaming multimedia en segundo plano y actualización de componentes.
"""

import json
import os
import subprocess
import threading
import time
import urllib.request

from config_manager import (
    get_base_dir,
    get_bin_dir,
    get_external_ytdlp_exe,
    get_ffmpeg_dir,
    get_cookie_args,
    get_cookie_ydl_opts
)

_yt_dlp = None
_ytdlp_ready = False


def _ensure_ytdlp():
    """Importa yt_dlp si está disponible y configura ffmpeg."""
    global _yt_dlp, _ytdlp_ready
    if _ytdlp_ready:
        return _yt_dlp
    try:
        import yt_dlp as _mod
        _yt_dlp = _mod
    except ImportError:
        _yt_dlp = None
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception:
        pass
    _ytdlp_ready = True
    return _yt_dlp


def get_current_version():
    """Obtiene la versión actual de yt-dlp instalada o descargada."""
    custom_exe = get_external_ytdlp_exe()
    if custom_exe:
        try:
            res = subprocess.run(
                [custom_exe, '--version'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
    yt_dlp = _ensure_ytdlp()
    if yt_dlp:
        return getattr(yt_dlp.version, '__version__', 'Desconocida')
    return "No instalada"


def check_nightly_version():
    """
    Consulta la API de GitHub para obtener la última versión Nightly disponible.
    Retorna (tag_name, download_url, release_date).
    """
    api_url = "https://api.github.com/repos/yt-dlp/yt-dlp-nightly-builds/releases/latest"
    req = urllib.request.Request(
        api_url,
        headers={'User-Agent': 'YouTubeDownloader-wx-App'}
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        if response.status == 200:
            data = json.loads(response.read().decode('utf-8'))
            tag_name = data.get('tag_name', '')
            published_at = data.get('published_at', '')
            download_url = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp.exe"
            return {
                'version': tag_name,
                'published_at': published_at,
                'download_url': download_url,
            }
    raise Exception("No se pudo obtener información de la versión Nightly desde GitHub.")


def download_file_with_progress(url, dest_path, progress_callback=None):
    """Descarga un archivo con notificación de progreso por callback."""
    req = urllib.request.Request(url, headers={'User-Agent': 'YouTubeDownloader-wx-App'})
    temp_path = dest_path + ".tmp"
    with urllib.request.urlopen(req, timeout=30) as response:
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        block_size = 65536

        with open(temp_path, 'wb') as f:
            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total_size > 0:
                    percent = int((downloaded / total_size) * 100)
                    progress_callback(percent, downloaded, total_size)

    if os.path.exists(dest_path):
        try:
            os.remove(dest_path)
        except Exception:
            pass
    os.replace(temp_path, dest_path)


_STREAM_CACHE = {}  # { (url_o_id, solo_audio): (stream_url, timestamp) }
_STREAM_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 4 * 3600  # 4 horas (URLs de CDN de YouTube son válidas ~6h)


def precargar_stream_en_segundo_plano(url_o_id, solo_audio=True):
    """
    Inicia la resolución predictiva de la URL de streaming en segundo plano
    y la deposita en caché para que el reproductor inicie el audio de forma instantánea.
    """
    if not url_o_id:
        return None
    key = (url_o_id, bool(solo_audio))
    with _STREAM_CACHE_LOCK:
        if key in _STREAM_CACHE:
            _, ts = _STREAM_CACHE[key]
            if time.time() - ts < _CACHE_TTL:
                return None
    def _worker():
        try:
            obtener_url_streaming(url_o_id, solo_audio=solo_audio)
        except Exception:
            pass
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t


def obtener_url_streaming(url_o_id, solo_audio=False):
    """
    Obtiene la URL directa de streaming (audio-only ultrarrápido o MP4/WebM con vídeo y audio combinados)
    usando yt-dlp para reproducir directamente en VLC sin descargar el archivo completo.
    Si solo_audio=True, obtiene exclusivamente el flujo de audio más ligero para un
    buffering casi instantáneo y transiciones inmediatas entre canciones.
    """
    original_input = url_o_id
    if not url_o_id.startswith('http'):
        url_o_id = f"https://www.youtube.com/watch?v={url_o_id}"

    with _STREAM_CACHE_LOCK:
        for k in [(url_o_id, bool(solo_audio)), (original_input, bool(solo_audio))]:
            if k in _STREAM_CACHE:
                cached_url, ts = _STREAM_CACHE[k]
                if time.time() - ts < _CACHE_TTL:
                    return cached_url
                else:
                    _STREAM_CACHE.pop(k, None)

    def _cache_and_return(res_url):
        if res_url:
            with _STREAM_CACHE_LOCK:
                _STREAM_CACHE[(url_o_id, bool(solo_audio))] = (res_url, time.time())
                _STREAM_CACHE[(original_input, bool(solo_audio))] = (res_url, time.time())
        return res_url

    custom_exe = get_external_ytdlp_exe()
    cookie_args = get_cookie_args()

    if solo_audio:
        fmt = 'ba/ba*/bestaudio/best[acodec!=none]/18/best'
    else:
        fmt = 'best[acodec!=none][vcodec!=none]/best[ext=mp4]/18/best'

    if custom_exe:
        intentos_cmd = []
        intentos_cmd.append([
            custom_exe,
            '-g',
            '-f', fmt,
            '--extractor-args', 'youtube:player_client=android,ios,web',
            '--no-warnings',
            '--quiet'
        ] + cookie_args + [url_o_id])

        if cookie_args:
            intentos_cmd.append([
                custom_exe,
                '-g',
                '-f', fmt,
                '--extractor-args', 'youtube:player_client=android',
                '--no-warnings',
                '--quiet',
                url_o_id
            ])

        for cmd in intentos_cmd:
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if res.returncode == 0 and res.stdout.strip():
                    urls = [u.strip() for u in res.stdout.strip().splitlines() if u.strip()]
                    if urls:
                        return _cache_and_return(urls[0])
            except Exception:
                pass

        intentos_json = []
        intentos_json.append([
            custom_exe,
            '--dump-single-json',
            '--no-download',
            '--no-warnings',
            '--quiet',
            '--extractor-args', 'youtube:player_client=android,ios,web'
        ] + cookie_args + [url_o_id])

        if cookie_args:
            intentos_json.append([
                custom_exe,
                '--dump-single-json',
                '--no-download',
                '--no-warnings',
                '--quiet',
                '--extractor-args', 'youtube:player_client=android',
                url_o_id
            ])

        for cmd_json in intentos_json:
            try:
                res_json = subprocess.run(
                    cmd_json,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=35,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if res_json.returncode == 0 and res_json.stdout.strip():
                    info = json.loads(res_json.stdout)
                    formats = info.get('formats', [])
                    if solo_audio:
                        audio_formats = [f['url'] for f in formats if f.get('url') and f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                        if audio_formats:
                            return _cache_and_return(audio_formats[-1])
                        combined_audio = [f['url'] for f in formats if f.get('url') and f.get('acodec') != 'none']
                        if combined_audio:
                            return _cache_and_return(combined_audio[-1])
                        if info.get('url'):
                            return _cache_and_return(info['url'])
                    else:
                        combined = [
                            f for f in formats 
                            if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none'
                        ]
                        if combined:
                            combined.sort(key=lambda f: (f.get('height') or 0, f.get('tbr') or 0))
                            return _cache_and_return(combined[-1]['url'])
                        hls_video = [
                            f['url'] for f in formats 
                            if 'manifest.googlevideo.com/api/manifest/hls_playlist' in f.get('url', '') and f.get('vcodec') != 'none'
                        ]
                        if hls_video:
                            return _cache_and_return(hls_video[-1])
                        if info.get('url'):
                            return _cache_and_return(info['url'])
            except Exception:
                pass

    yt_dlp = _ensure_ytdlp()
    if yt_dlp:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}}
        }
        ydl_opts.update(get_cookie_ydl_opts())
        if solo_audio:
            ydl_opts['format'] = fmt

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url_o_id, download=False)
                formats = info.get('formats', [])

                if solo_audio:
                    audio_formats = [f['url'] for f in formats if f.get('url') and f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                    if audio_formats:
                        return _cache_and_return(audio_formats[-1])
                    combined_audio = [f['url'] for f in formats if f.get('url') and f.get('acodec') != 'none']
                    if combined_audio:
                        return _cache_and_return(combined_audio[-1])
                    if info.get('url'):
                        return _cache_and_return(info['url'])

                combined = [
                    f for f in formats 
                    if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none'
                ]
                if combined:
                    combined.sort(key=lambda f: (f.get('height') or 0, f.get('tbr') or 0))
                    return _cache_and_return(combined[-1]['url'])

                hls_video = [
                    f['url'] for f in formats 
                    if 'manifest.googlevideo.com/api/manifest/hls_playlist' in f.get('url', '') and f.get('vcodec') != 'none'
                ]
                if hls_video:
                    return _cache_and_return(hls_video[-1])

                if info.get('url'):
                    return _cache_and_return(info['url'])
        except Exception:
            pass

    raise RuntimeError("No se pudo obtener el flujo directo multimedia para reproducir. El vídeo podría tener restricciones de YouTube o requerir actualización de componentes.")
