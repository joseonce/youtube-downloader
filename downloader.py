"""
Módulo principal del descargador de YouTube y punto de unión modular.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.parse

from config_manager import (
    DEFAULT_CONFIG,
    get_base_dir,
    get_config_dir,
    get_config_file_path,
    get_bin_dir,
    get_docs_dir,
    get_resources_dir,
    get_app_data_dir,
    get_external_ytdlp_exe,
    get_ffmpeg_dir,
    abrir_manual_usuario,
    abrir_atajos_teclado,
    cargar_configuracion,
    guardar_configuracion,
    get_cookie_args,
    get_cookie_ydl_opts,
    probar_conexion_sesion
)

from favorites_manager import (
    get_favoritos_dir,
    get_favoritos_file_path,
    cargar_favoritos,
    guardar_favoritos,
    guardar_lista_favoritos,
    eliminar_lista_favoritos,
    obtener_listas_favoritos,
    obtener_nombres_listas_favoritos,
    obtener_favoritos,
    detectar_tipo_elemento,
    agregar_favorito,
    crear_lista_favoritos,
    eliminar_favorito,
    es_favorito,
    obtener_listas_de_item,
    mover_favorito_de_lista
)

from media_utils import (
    formatear_duracion,
    formatear_visitas,
    formatear_tamano,
    limpiar_caracteres_ansi,
    limpiar_extension_titulo,
    corregir_doble_extension,
    identificar_tipo_url
)

from streaming import (
    _ensure_ytdlp,
    get_current_version,
    check_nightly_version,
    download_file_with_progress,
    precargar_stream_en_segundo_plano,
    obtener_url_streaming
)


class YouTubeDownloader:
    def __init__(self):
        self._cancel_requested = False
        self._active_process = None
        self.last_container_title = ""
        self.config = cargar_configuracion()

    def request_cancel(self):
        """Solicita la cancelación de la descarga activa."""
        self._cancel_requested = True
        proc = self._active_process
        if proc:
            try:
                proc.terminate()
                if os.name == 'nt' and hasattr(proc, 'pid') and proc.pid:
                    try:
                        subprocess.run(
                            ['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                            capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    except Exception:
                        pass
            except Exception:
                pass

    def is_cancelled(self):
        return self._cancel_requested

    def _procesar_entries(self, entries, max_results=50, is_playlist_list=False, is_channel_list=False, query='', start_index=1, parent_channel_url=''):
        """
        Convierte una lista de entradas de yt-dlp a nuestro formato estándar,
        respetando fielmente la ordenación y criterios naturales por defecto de yt-dlp.
        """
        if not entries:
            return []

        resultados = []
        for idx, entry in enumerate(entries[:max_results], start_index):
            if not entry:
                continue
            item_id = entry.get('id', '')
            titulo = limpiar_extension_titulo(entry.get('title', 'Sin título'))
            canal = entry.get('uploader') or entry.get('channel') or entry.get('channel_title') or entry.get('creator') or 'Desconocido'
            
            entry_url = str(entry.get('url', ''))
            entry_id = str(entry.get('id', ''))
            web_url = str(entry.get('webpage_url') or entry.get('original_url') or entry_url)
            entry_type = entry.get('_type', '')

            es_video = (entry_type == 'video') or ('watch?v=' in web_url) or ('/shorts/' in web_url) or ('watch?v=' in entry_url)

            es_canal = (not es_video) and (is_channel_list or (
                entry_type == 'channel' or
                ('/channel/' in entry_url and 'watch' not in entry_url) or
                ('/@' in entry_url and 'watch' not in entry_url) or
                ('/c/' in entry_url and 'watch' not in entry_url) or
                ('/user/' in entry_url and 'watch' not in entry_url)
            ))
            
            es_playlist = (not es_video) and (not es_canal) and (
                is_playlist_list or
                entry_type == 'playlist' or
                entry.get('playlist_count') is not None or
                'playlist?list=' in entry_url or
                '/playlist' in entry_url or
                (entry_id.startswith('PL') and 'watch' not in entry_url)
            )

            if es_canal:
                titulo = entry.get('title') or entry.get('channel') or entry.get('uploader') or 'Canal'
                canal = entry.get('channel') or entry.get('uploader') or entry.get('uploader_id') or 'Canal'
                subs = entry.get('channel_follower_count') or entry.get('subscriber_count')
                if subs is not None:
                    try:
                        subs_num = int(subs)
                        if subs_num >= 1_000_000:
                            subs_str = f"{subs_num / 1_000_000:.1f}M suscriptores".replace('.0M', 'M')
                        elif subs_num >= 1_000:
                            subs_str = f"{subs_num / 1_000:.1f}K suscriptores".replace('.0K', 'K')
                        else:
                            subs_str = f"{subs_num} suscriptores"
                    except Exception:
                        subs_str = f"{subs} suscriptores"
                else:
                    subs_str = "--"

                # Comprobar si yt-dlp proporciona el número de vídeos del canal
                vid_count = (
                    entry.get('video_count') or 
                    entry.get('item_count')
                )
                if vid_count:
                    try:
                        vid_count_num = int(vid_count)
                        vids_label = f"{vid_count_num} vídeos"
                    except Exception:
                        vids_label = f"{vid_count} vídeos"
                    duracion_str = vids_label
                    if subs_str != "--":
                        views_str = f"{subs_str} • {vids_label}"
                    else:
                        views_str = vids_label
                else:
                    duracion_str = "Canal"
                    views_str = subs_str

                duracion_sec = 0
                url = entry.get('channel_url') or entry.get('uploader_url') or (f"https://www.youtube.com/channel/{item_id}" if item_id and not item_id.startswith('http') else entry_url)
                tipo_item = 'channel'
                vc = subs
                channel_url = url
            elif es_playlist:
                item_count = entry.get('playlist_count') or entry.get('item_count')
                duracion_str = f"{item_count} vídeos" if item_count else "Lista de reproducción"
                views_str = f"{item_count} vídeos" if item_count else "--"
                duracion_sec = 0
                url = entry.get('webpage_url') or (f"https://www.youtube.com/playlist?list={item_id}" if item_id and not item_id.startswith('http') else entry_url)
                tipo_item = 'playlist'
                vc = None
                channel_url = (
                    entry.get('uploader_url') or
                    entry.get('channel_url') or
                    (f"https://www.youtube.com/channel/{entry.get('channel_id')}" if entry.get('channel_id') else '') or
                    (f"https://www.youtube.com/{entry.get('uploader_id')}" if entry.get('uploader_id') and str(entry.get('uploader_id')).startswith('@') else '') or
                    parent_channel_url or ''
                )
            else:
                duracion_sec = entry.get('duration')
                duracion_str = formatear_duracion(duracion_sec)
                url = entry.get('webpage_url') or entry.get('original_url') or (f"https://www.youtube.com/watch?v={item_id}" if item_id and not item_id.startswith('http') else entry_url)
                tipo_item = 'video'
                vc = entry.get('view_count')
                if vc is None:
                    vc = entry.get('views')
                views_str = formatear_visitas(vc)
                channel_url = (
                    entry.get('uploader_url') or
                    entry.get('channel_url') or
                    (f"https://www.youtube.com/channel/{entry.get('channel_id')}" if entry.get('channel_id') else '') or
                    (f"https://www.youtube.com/{entry.get('uploader_id')}" if entry.get('uploader_id') and str(entry.get('uploader_id')).startswith('@') else '') or
                    parent_channel_url or ''
                )

            resultados.append({
                'index': idx,
                'id': item_id or str(idx),
                'title': titulo,
                'channel': canal,
                'channel_url': channel_url,
                'duration_seconds': duracion_sec,
                'duration': duracion_str,
                'views': views_str,
                'view_count': vc,
                'url': url,
                'description': entry.get('description') or '',
                'is_playlist': (tipo_item == 'playlist'),
                'is_channel': (tipo_item == 'channel'),
                'tipo_item': tipo_item,
                'selected': False,
            })
        return resultados

    def extraer_info_contenedor(self, target_url: str, tipo_contenedor: str) -> list:
        """
        Extrae la información y metadatos de un contenedor (canal o lista de reproducción)
        como un único elemento de resultado, sin extraer su contenido interno de vídeos.
        tipo_contenedor puede ser 'channel' o 'playlist'.
        """
        self._cancel_requested = False
        target_url = target_url.strip()
        if not target_url:
            return []

        if target_url.startswith('@'):
            target_url = f"https://www.youtube.com/{target_url}"

        is_channel = (tipo_contenedor == 'channel')
        is_playlist = (tipo_contenedor == 'playlist')

        clean_url = target_url
        if is_channel:
            clean_url = re.sub(r'/(?:videos|playlists|featured|shorts|community|podcasts)$', '', target_url.rstrip('/'))
        elif is_playlist and 'list=' in clean_url and 'playlist?list=' not in clean_url:
            m = re.search(r'[?&]list=([a-zA-Z0-9_-]+)', clean_url)
            if m:
                clean_url = f"https://www.youtube.com/playlist?list={m.group(1)}"

        custom_exe = get_external_ytdlp_exe()
        cookie_args = get_cookie_args()
        last_error = ""

        if custom_exe:
            intentos_cookies = [cookie_args, []] if cookie_args else [[]]
            for c_args in intentos_cookies:
                try:
                    cmd = [
                        custom_exe,
                        clean_url,
                        "--dump-single-json",
                        "--flat-playlist",
                        "--no-download",
                        "--no-warnings",
                        "--playlist-items", "0",
                        "--extractor-args", "youtube:player_client=android,ios,web"
                    ] + c_args
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=35,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        info = json.loads(res.stdout)
                        self.last_container_title = info.get('title') or ''
                        if is_channel and not info.get('channel_url') and not info.get('uploader_url'):
                            info['channel_url'] = clean_url
                        if is_playlist and not info.get('webpage_url'):
                            info['webpage_url'] = clean_url
                        entries = [info]
                        return self._procesar_entries(entries, max_results=1, is_channel_list=is_channel, is_playlist_list=is_playlist, query=target_url)
                    if res.stderr and res.stderr.strip():
                        last_error = res.stderr.strip()
                except Exception as e:
                    last_error = str(e)

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'playlist_items': '0',
            'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}}
        }
        ydl_opts.update(get_cookie_ydl_opts())

        yt_dlp = _ensure_ytdlp()
        if yt_dlp:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(clean_url, download=False)
                    self.last_container_title = info.get('title') or ''
                    if is_channel and not info.get('channel_url') and not info.get('uploader_url'):
                        info['channel_url'] = clean_url
                    if is_playlist and not info.get('webpage_url'):
                        info['webpage_url'] = clean_url
                    entries = [info]
                    return self._procesar_entries(entries, max_results=1, is_channel_list=is_channel, is_playlist_list=is_playlist, query=target_url)
            except Exception as e:
                last_error = str(e)

        if not custom_exe and not yt_dlp:
            raise RuntimeError("No se encuentra la librería necesaria (yt-dlp.exe) para la ejecución del programa.")

        if last_error:
            raise RuntimeError(last_error)
        return []

    def buscar(self, query: str, max_results: int = 25, engine: str = 'ytsearch', search_type: str = 'video', start_index: int = 1):
        """
        Realiza una búsqueda de vídeos, canales o listas de reproducción en la plataforma seleccionada o analiza una URL directa.
        Soporta motores de búsqueda (ytsearch, scsearch, bcsearch, bilisearch, gvsearch) o URLs directas.
        search_type puede ser 'video', 'channel' o 'playlist'.
        start_index permite paginar los resultados a partir de una posición inicial (1-indexed).
        """
        self._cancel_requested = False
        query = query.strip()
        if not query:
            return []

        tipo_url = identificar_tipo_url(query)
        if tipo_url == 'canal':
            return self.extraer_info_contenedor(query, tipo_contenedor='channel')
        elif tipo_url == 'playlist':
            return self.extraer_info_contenedor(query, tipo_contenedor='playlist')

        is_channel_search = False
        is_playlist_search = False

        end_index = max(start_index, start_index + max_results - 1)

        # Determinar el término de consulta final
        if query.startswith('http://') or query.startswith('https://'):
            search_query = query
        else:
            if engine == 'ytsearch':
                if search_type == 'channel':
                    search_query = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}&sp=EgIQAg%253D%253D"
                    is_channel_search = True
                elif search_type == 'playlist':
                    search_query = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}&sp=EgIQAw%253D%253D"
                    is_playlist_search = True
                else:
                    # Búsqueda estándar de vídeos por defecto en yt-dlp
                    search_query = f"ytsearch{end_index}:{query}"
            else:
                search_prefix = engine if engine.endswith('search') else f"{engine}search"
                search_query = f"{search_prefix}{end_index}:{query}"

        # Si existe un yt-dlp.exe externo actualizado, se usa dinámicamente
        custom_exe = get_external_ytdlp_exe()
        cookie_args = get_cookie_args()
        last_error = ""
        if custom_exe:
            # Si hay cookies configuradas, probamos con cookies y si falla probamos sin ellas como fallback
            intentos_cookies = [cookie_args, []] if cookie_args else [[]]
            for c_args in intentos_cookies:
                try:
                    cmd = [
                        custom_exe,
                        search_query,
                        "--dump-single-json",
                        "--flat-playlist",
                        "--no-download",
                        "--no-warnings",
                        "--playlist-items", f"{start_index}-{end_index}",
                        "--extractor-args", "youtube:player_client=android,ios,web"
                    ] + c_args
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=35,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        info = json.loads(res.stdout)
                        entries = info.get('entries')
                        if entries is None:
                            entries = [info] if info.get('title') else []
                        parent_ch = info.get('uploader_url') or info.get('channel_url') or ''
                        return self._procesar_entries(
                            entries,
                            max_results=max_results,
                            is_playlist_list=is_playlist_search,
                            is_channel_list=is_channel_search,
                            query=query,
                            start_index=start_index,
                            parent_channel_url=parent_ch
                        )
                    if res.stderr and res.stderr.strip():
                        last_error = res.stderr.strip()
                except Exception as e:
                    last_error = str(e)

        # Uso de la librería en proceso (si estuviera disponible en modo desarrollo)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'playlist_items': f'{start_index}-{end_index}',
            'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}}
        }
        ydl_opts.update(get_cookie_ydl_opts())

        yt_dlp = _ensure_ytdlp()
        if yt_dlp:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(search_query, download=False)
                entries = info.get('entries')
                if entries is None:
                    entries = [info] if info.get('title') else []

                parent_ch = info.get('uploader_url') or info.get('channel_url') or ''
                return self._procesar_entries(
                    entries,
                    max_results=max_results,
                    is_playlist_list=is_playlist_search,
                    is_channel_list=is_channel_search,
                    query=query,
                    start_index=start_index,
                    parent_channel_url=parent_ch
                )
            except Exception as e:
                last_error = str(e)

        if not custom_exe and not yt_dlp:
            raise RuntimeError("No se encuentra la librería necesaria (yt-dlp.exe) para la ejecución del programa.")

        if last_error:
            raise RuntimeError(last_error)
        return []

    def buscar_canal_videos(self, channel_url: str, max_results: int = 25, start_index: int = 1):
        """Extrae la lista de vídeos subidos por un canal."""
        self._cancel_requested = False
        channel_url = channel_url.strip()
        if channel_url.startswith('@'):
            channel_url = f"https://www.youtube.com/{channel_url}"
        
        base = channel_url.rstrip('/')
        base = re.sub(r'/(?:videos|playlists|featured|shorts|community|podcasts)$', '', base)
        url_final = f"{base}/videos"

        # 1. Intentamos obtener la pestaña '/videos' (lo habitual para creadores de contenido estándar)
        try:
            res = self._extraer_flat_url(url_final, max_results=max_results, is_playlist_list=False, query=channel_url, start_index=start_index)
            if res:
                return res
        except Exception as e:
            # Si el canal no tiene pestaña '/videos' (canales temáticos de música tipo 'Topic', perfiles generados automáticamente, etc.),
            # o falla al pedir /videos, reintentamos con la URL base del canal donde yt-dlp redirige a las pistas/subidas.
            try:
                return self._extraer_flat_url(base, max_results=max_results, is_playlist_list=False, query=channel_url, start_index=start_index)
            except Exception:
                raise e

        # Si url_final no arrojó excepción pero devolvió lista vacía en la primera página,
        # probamos con la URL base del canal
        if start_index == 1:
            try:
                res_base = self._extraer_flat_url(base, max_results=max_results, is_playlist_list=False, query=channel_url, start_index=start_index)
                if res_base:
                    return res_base
            except Exception:
                pass

        return []

    def buscar_canal_playlists(self, channel_url: str, max_results: int = 25, start_index: int = 1):
        """Extrae las listas de reproducción públicas de un canal."""
        self._cancel_requested = False
        channel_url = channel_url.strip()
        if channel_url.startswith('@'):
            channel_url = f"https://www.youtube.com/{channel_url}"
        
        base = channel_url.rstrip('/')
        base = re.sub(r'/(?:videos|playlists|featured|shorts|community|podcasts)$', '', base)
        url_final = f"{base}/playlists"

        try:
            return self._extraer_flat_url(url_final, max_results=max_results, is_playlist_list=True, query=channel_url, start_index=start_index)
        except Exception as e:
            err_msg = str(e).lower()
            if "does not have a playlists tab" in err_msg or "no tiene" in err_msg:
                return []
            raise

    def buscar_playlist_videos(self, playlist_url: str, max_results: int = 100, start_index: int = 1):
        """Extrae los vídeos de una lista de reproducción."""
        self._cancel_requested = False
        return self._extraer_flat_url(playlist_url.strip(), max_results=max_results, is_playlist_list=False, query=playlist_url, start_index=start_index)

    def _extraer_flat_url(self, target_url: str, max_results: int = 50, is_playlist_list: bool = False, query: str = '', start_index: int = 1):
        """Método unificado para extraer entradas usando CLI externa o librería interna con paginación."""
        end_index = max(start_index, start_index + max_results - 1)
        custom_exe = get_external_ytdlp_exe()
        cookie_args = get_cookie_args()
        last_error = ""
        is_private_only = any(x in target_url for x in ['/history', '/feed/playlists', 'list=WL'])
        if custom_exe:
            intentos_cookies = [cookie_args, []] if (cookie_args and not is_private_only) else [cookie_args]
            for c_args in intentos_cookies:
                try:
                    cmd = [
                        custom_exe,
                        target_url,
                        "--dump-single-json",
                        "--flat-playlist",
                        "--no-download",
                        "--no-warnings",
                        "--playlist-items", f"{start_index}-{end_index}",
                        "--extractor-args", "youtube:player_client=android,ios,web"
                    ] + c_args
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=45,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        info = json.loads(res.stdout)
                        self.last_container_title = info.get('title') or ''
                        entries = list(info.get('entries') or [])
                        if not entries and info.get('title') and not is_playlist_list:
                            entries = [info]
                        parent_ch = info.get('uploader_url') or info.get('channel_url') or ''
                        return self._procesar_entries(entries, max_results=max_results, is_playlist_list=is_playlist_list, query=query, start_index=start_index, parent_channel_url=parent_ch)
                    if res.stderr and res.stderr.strip():
                        last_error = res.stderr.strip()
                except Exception as e:
                    last_error = str(e)

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
            'playlist_items': f'{start_index}-{end_index}',
            'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}}
        }
        ydl_opts.update(get_cookie_ydl_opts())

        yt_dlp = _ensure_ytdlp()
        if yt_dlp:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(target_url, download=False)
                    self.last_container_title = info.get('title') or ''
                    entries = list(info.get('entries') or [])
                    if not entries and info.get('title') and not is_playlist_list:
                        entries = [info]
                    parent_ch = info.get('uploader_url') or info.get('channel_url') or ''
                    return self._procesar_entries(entries, max_results=max_results, is_playlist_list=is_playlist_list, query=query, start_index=start_index, parent_channel_url=parent_ch)
            except Exception as e:
                last_error = str(e)

        if not custom_exe and not yt_dlp:
            raise RuntimeError("No se encuentra la librería necesaria (yt-dlp.exe) para la ejecución del programa.")

        if last_error:
            raise RuntimeError(last_error)
        return []

    def buscar_historial(self, max_results: int = 50, start_index: int = 1):
        """Extrae las entradas del Historial de reproducciones de YouTube del usuario."""
        self._cancel_requested = False
        return self._extraer_flat_url(
            "https://www.youtube.com/feed/history",
            max_results=max_results,
            is_playlist_list=False,
            query="Historial de YouTube",
            start_index=start_index
        )

    def buscar_ver_mas_tarde(self, max_results: int = 50, start_index: int = 1):
        """Extrae las entradas de la lista 'Ver más tarde' del usuario."""
        self._cancel_requested = False
        return self._extraer_flat_url(
            "https://www.youtube.com/playlist?list=WL",
            max_results=max_results,
            is_playlist_list=False,
            query="Ver más tarde",
            start_index=start_index
        )

    def buscar_mis_playlists(self, max_results: int = 50, start_index: int = 1):
        """Extrae las listas de reproducción de la cuenta del usuario."""
        self._cancel_requested = False
        return self._extraer_flat_url(
            "https://www.youtube.com/feed/playlists",
            max_results=max_results,
            is_playlist_list=True,
            query="Mis listas de reproducción",
            start_index=start_index
        )

    def descargar(self, url: str, formato: str, destino: str,
                  on_progress=None, on_finished=None, on_error=None):
        """
        Descarga un vídeo o audio de YouTube en un hilo secundario.
        Aplica inmediatamente el motor yt-dlp actualizado si existe.
        """
        self._cancel_requested = False

        def _worker():
            custom_exe = get_external_ytdlp_exe()
            cfg = getattr(self, 'config', None) or cargar_configuracion()
            last_download_error = ""

            # --- SI HAY UN MOTOR EXTERNO ACTUALIZADO A NIGHTLY ---
            if custom_exe:
                try:
                    outtmpl = os.path.join(destino, '%(title)s.%(ext)s')
                    base_args = [
                        custom_exe,
                        url,
                        "--output", outtmpl,
                        "--newline",
                        "--no-warnings",
                        "--replace-in-metadata", "title", r"(?i)\.(mp4|flv|mkv|webm|avi|wmv|mov|m4v|3gp|vob|ogv|divx|mp3|m4a|aac|wav|flac|ogg|opus|wma)$", "",
                        "--extractor-args", "youtube:player_client=android,ios,web"
                    ]

                    ffmpeg_dir = get_ffmpeg_dir()
                    if ffmpeg_dir:
                        base_args.extend(["--ffmpeg-location", ffmpeg_dir])

                    if formato == 'audio_mp3_192':
                        fmt_args = ["-x", "--audio-format", "mp3", "--audio-quality", "192K"]
                    elif formato == 'audio_mp3_320':
                        fmt_args = ["-x", "--audio-format", "mp3", "--audio-quality", "320K"]
                    elif formato == 'audio_m4a':
                        fmt_args = ["-x", "--audio-format", "m4a"]
                    elif formato == 'audio_flac':
                        fmt_args = ["-x", "--audio-format", "flac"]
                    elif formato == 'audio_wav':
                        fmt_args = ["-x", "--audio-format", "wav"]
                    else:  # video_best
                        fmt_args = ["-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4"]

                    def _run_download_process(extra_args):
                        cmd = base_args + extra_args + fmt_args
                        proc = subprocess.Popen(
                            cmd,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            encoding='utf-8',
                            errors='replace',
                            bufsize=1,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                        )
                        self._active_process = proc

                        prog_regex = re.compile(
                            r'\[download\]\s+([\d\.]+)%\s+of\s+(?:~?\s*([\d\.]+\w+))?\s+at\s+([\d\.]+\w+/s|\S+)\s+ETA\s+(\S+)',
                            re.IGNORECASE
                        )

                        last_percent = 0.0
                        last_output_lines = []
                        detected_file = ""

                        for line in proc.stdout:
                            stripped = line.strip()
                            if stripped:
                                last_output_lines.append(stripped)
                                if len(last_output_lines) > 25:
                                    last_output_lines.pop(0)

                            if self._cancel_requested:
                                proc.terminate()
                                raise Exception("Descarga cancelada por el usuario.")

                            if "Destination:" in stripped:
                                parts = stripped.split("Destination:", 1)
                                if len(parts) > 1 and parts[1].strip():
                                    detected_file = parts[1].strip()
                            elif "Merging formats into" in stripped:
                                parts = stripped.split("Merging formats into", 1)
                                if len(parts) > 1:
                                    detected_file = parts[1].strip(' "\'')

                            match = prog_regex.search(line)
                            if match and on_progress:
                                percent_val = float(match.group(1))
                                last_percent = percent_val
                                total_val = match.group(2) or "Desconocido"
                                speed_val = match.group(3) or "Calculando..."
                                eta_val = match.group(4) or "--:--"

                                on_progress({
                                    'status': 'downloading',
                                    'percent': percent_val,
                                    'speed': speed_val,
                                    'eta': eta_val,
                                    'downloaded': f"{percent_val:.1f}%",
                                    'total': total_val,
                                    'filename': os.path.basename(detected_file) if detected_file else 'Vídeo',
                                })
                            elif "[ExtractAudio]" in line or "[Merger]" in line:
                                if on_progress:
                                    on_progress({
                                        'status': 'processing',
                                        'percent': 100.0,
                                        'message': 'Procesando y guardando archivo final...',
                                        'filename': os.path.basename(detected_file) if detected_file else 'Vídeo',
                                    })

                        proc.wait()
                        self._active_process = None

                        if self._cancel_requested:
                            raise Exception("Descarga cancelada por el usuario.")

                        return proc.returncode, last_output_lines, detected_file

                    cookie_args = get_cookie_args(cfg)
                    returncode = -1
                    last_output_lines = []
                    detected_file = ""

                    # Intento 1: con cookies si están configuradas
                    if cookie_args:
                        returncode, last_output_lines, detected_file = _run_download_process(cookie_args)

                    # Si no hay cookies o el intento con cookies falló (cookies inválidas, bloqueo o falta de JS runtime),
                    # reintentamos automáticamente en modo estándar sin cookies
                    if (returncode != 0 or not cookie_args) and not self._cancel_requested:
                        if cookie_args and returncode != 0 and on_progress:
                            on_progress({
                                'status': 'downloading',
                                'percent': 0.0,
                                'speed': '',
                                'eta': '',
                                'downloaded': '0%',
                                'total': 'Reintentando...',
                                'filename': 'Reintentando sin cookies de sesión...',
                            })
                        returncode, last_output_lines, detected_file = _run_download_process([])

                    if returncode == 0:
                        if detected_file:
                            cleaned_path = corregir_doble_extension(detected_file)
                            if cleaned_path != detected_file and os.path.exists(detected_file):
                                try:
                                    if not os.path.exists(cleaned_path):
                                        os.rename(detected_file, cleaned_path)
                                        detected_file = cleaned_path
                                except Exception:
                                    pass

                        if on_finished:
                            titulo_final = os.path.splitext(os.path.basename(detected_file))[0] if detected_file else 'Vídeo'
                            on_finished({
                                'title': titulo_final,
                                'filepath': detected_file if detected_file else destino,
                                'directory': destino,
                            })
                        return
                    else:
                        error_lines = [l for l in last_output_lines if 'error' in l.lower() or 'warning' in l.lower()]
                        error_detail = "\n".join(error_lines) if error_lines else ("\n".join(last_output_lines[-5:]) if last_output_lines else f"Código {returncode}")
                        raise Exception(f"El proceso finalizó con código {returncode}: {error_detail}")

                except Exception as ex:
                    last_download_error = str(ex)
                    if self._cancel_requested or "Descarga cancelada" in str(ex):
                        if on_error:
                            on_error("Descarga cancelada por el usuario.", cancelled=True)
                        return
                    # Si falla el binario externo, continúa con el fallback de la librería interna

            # --- FALLBACK / USO DE LIBRERÍA INTERNA yt_dlp ---
            def _progress_hook(d):
                if self._cancel_requested:
                    raise Exception("Descarga cancelada por el usuario.")

                if on_progress is None:
                    return

                status = d.get('status')
                if status == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes') or 0
                    speed = d.get('speed') or 0
                    eta = d.get('eta')

                    porcentaje = 0.0
                    if total > 0:
                        porcentaje = (downloaded / total) * 100.0
                    elif '_percent_str' in d:
                        raw_str = limpiar_caracteres_ansi(d.get('_percent_str', '0%')).replace('%', '').strip()
                        try:
                            porcentaje = float(raw_str)
                        except ValueError:
                            porcentaje = 0.0

                    speed_str = f"{formatear_tamano(speed)}/s" if speed else "Calculando..."
                    eta_str = formatear_duracion(eta) if eta is not None else "--:--"
                    descargado_str = formatear_tamano(downloaded)
                    total_str = formatear_tamano(total) if total else "Desconocido"

                    info_dict = {
                        'status': 'downloading',
                        'percent': porcentaje,
                        'speed': speed_str,
                        'eta': eta_str,
                        'downloaded': descargado_str,
                        'total': total_str,
                        'filename': os.path.basename(d.get('filename', '')),
                    }
                    on_progress(info_dict)

                elif status == 'finished':
                    info_dict = {
                        'status': 'processing',
                        'percent': 100.0,
                        'message': 'Procesando y guardando archivo final...',
                        'filename': os.path.basename(d.get('filename', '')),
                    }
                    on_progress(info_dict)

            try:
                outtmpl = os.path.join(destino, '%(title)s.%(ext)s')
                ydl_opts = {
                    'outtmpl': outtmpl,
                    'progress_hooks': [_progress_hook],
                    'quiet': True,
                    'no_warnings': True,
                    'parse_metadata': {'pre_process': [('title', r'(?i)\.(mp4|flv|mkv|webm|avi|wmv|mov|m4v|3gp|vob|ogv|divx|mp3|m4a|aac|wav|flac|ogg|opus|wma)$', '')]},
                    'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}},
                }
                cookie_opts = get_cookie_ydl_opts(cfg)
                ydl_opts.update(cookie_opts)

                if formato == 'audio_mp3_192':
                    ydl_opts.update({
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                    })
                elif formato == 'audio_mp3_320':
                    ydl_opts.update({
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '320',
                        }],
                    })
                elif formato == 'audio_m4a':
                    ydl_opts.update({
                        'format': 'bestaudio[ext=m4a]/bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'm4a',
                        }],
                    })
                elif formato == 'audio_flac':
                    ydl_opts.update({
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'flac',
                        }],
                    })
                elif formato == 'audio_wav':
                    ydl_opts.update({
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'wav',
                        }],
                    })
                else:  # 'video_best'
                    ydl_opts.update({
                        'format': 'bestvideo+bestaudio/best',
                        'merge_output_format': 'mp4',
                    })

                ffmpeg_dir = get_ffmpeg_dir()
                if ffmpeg_dir:
                    ydl_opts['ffmpeg_location'] = ffmpeg_dir

                yt_dlp = _ensure_ytdlp()
                if not yt_dlp:
                    if on_error:
                        err_msg = last_download_error if last_download_error else (
                            "No se encuentra la librería necesaria (yt-dlp.exe) para la ejecución del programa." if not custom_exe else "Error al procesar la descarga."
                        )
                        on_error(err_msg, cancelled=False)
                    return

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                except Exception:
                    # Si falló con cookies en la librería interna, reintentar sin cookies
                    if cookie_opts:
                        for k in cookie_opts:
                            ydl_opts.pop(k, None)
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(url, download=True)
                    else:
                        raise

                titulo = limpiar_extension_titulo(info.get('title', 'Vídeo'))
                ext = 'mp3' if 'mp3' in formato else ('m4a' if 'm4a' in formato else ('flac' if 'flac' in formato else ('wav' if 'wav' in formato else 'mp4')))
                nombre_archivo = f"{titulo}.{ext}"
                ruta_completa = os.path.join(destino, nombre_archivo)
                try:
                    if os.path.exists(destino):
                        for fname in os.listdir(destino):
                            if fname.endswith(f".{ext}"):
                                c_fname = corregir_doble_extension(fname)
                                if c_fname != fname:
                                    old_p = os.path.join(destino, fname)
                                    new_p = os.path.join(destino, c_fname)
                                    if os.path.exists(old_p) and not os.path.exists(new_p):
                                        os.rename(old_p, new_p)
                                        if fname == nombre_archivo or fname.startswith(titulo):
                                            ruta_completa = new_p
                except Exception:
                    pass

                if on_finished and not self._cancel_requested:
                    on_finished({
                        'title': titulo,
                        'filepath': ruta_completa,
                        'directory': destino,
                    })

            except Exception as e:
                error_msg = str(e)
                if self._cancel_requested or "Descarga cancelada" in error_msg:
                    if on_error:
                        on_error("Descarga cancelada por el usuario.", cancelled=True)
                else:
                    if on_error:
                        on_error(error_msg, cancelled=False)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def obtener_canal_url(self, target_url: str) -> str:
        """
        Obtiene la URL del canal al que pertenece un vídeo o playlist usando CLI externa o librería interna.
        """
        custom_exe = get_external_ytdlp_exe()
        if custom_exe:
            try:
                cmd = [
                    custom_exe,
                    target_url,
                    "--dump-single-json",
                    "--flat-playlist",
                    "--no-download",
                    "--quiet",
                    "--no-warnings",
                    "--playlist-items", "1",
                    "--extractor-args", "youtube:player_client=android,ios,web"
                ]
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
                    info = json.loads(res.stdout)
                    ch_url = (
                        info.get('uploader_url') or
                        info.get('channel_url') or
                        (f"https://www.youtube.com/channel/{info.get('channel_id')}" if info.get('channel_id') else '') or
                        (f"https://www.youtube.com/{info.get('uploader_id')}" if info.get('uploader_id') and str(info.get('uploader_id')).startswith('@') else '')
                    )
                    if ch_url:
                        return ch_url
            except Exception:
                pass

        yt_dlp = _ensure_ytdlp()
        if yt_dlp:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'skip_download': True,
                'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}}
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(target_url, download=False)
                    return (
                        info.get('uploader_url') or
                        info.get('channel_url') or
                        (f"https://www.youtube.com/channel/{info.get('channel_id')}" if info.get('channel_id') else '') or
                        (f"https://www.youtube.com/{info.get('uploader_id')}" if info.get('uploader_id') and str(info.get('uploader_id')).startswith('@') else '') or
                        ""
                    )
            except Exception:
                pass
        return ""

    def obtener_descripcion(self, target_url: str) -> str:
        """
        Obtiene la descripción completa de un vídeo, lista de reproducción o canal usando CLI externa o librería interna.
        """
        custom_exe = get_external_ytdlp_exe()
        cookie_args = get_cookie_args()
        if custom_exe:
            intentos_cookies = [cookie_args, []] if cookie_args else [[]]
            for c_args in intentos_cookies:
                try:
                    cmd = [
                        custom_exe,
                        target_url,
                        "--dump-single-json",
                        "--flat-playlist",
                        "--no-download",
                        "--quiet",
                        "--no-warnings",
                        "--playlist-items", "1",
                        "--extractor-args", "youtube:player_client=android,ios,web"
                    ] + c_args
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
                        info = json.loads(res.stdout)
                        if isinstance(info, dict):
                            desc = info.get('description')
                            if desc is not None:
                                return desc
                except Exception:
                    pass

        yt_dlp = _ensure_ytdlp()
        if yt_dlp:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'skip_download': True,
                'playlist_items': '1',
                'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}}
            }
            ydl_opts.update(get_cookie_ydl_opts())
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(target_url, download=False)
                    if isinstance(info, dict):
                        return info.get('description') or ""
            except Exception:
                pass
        return ""
