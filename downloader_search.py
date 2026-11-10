"""

Módulo de búsqueda, extracción de metadatos y navegación en YouTube.

Proporciona YouTubeSearchMixin para desacoplar las consultas del motor de descarga.

"""



import json

import os

import re

import subprocess

import time

import unicodedata

import urllib.parse



from config_manager import (

    get_external_ytdlp_exe,

    cargar_configuracion,

    get_ytdlp_extractor_args,

    get_ytdlp_clients_list,

)

from media_utils import (

    formatear_duracion,

    formatear_visitas,

    limpiar_extension_titulo,

    identificar_tipo_url,

)

from streaming import _ensure_ytdlp







class YouTubeSearchMixin:

    """

    Mixin que contiene la lógica de búsqueda, consulta y extracción de metadatos.

    """

    def _procesar_entries(self, entries, max_results=50, is_playlist_list=False, is_channel_list=False, query='', start_index=1, parent_channel_url='', parent_channel_name=''):

        """

        Convierte una lista de entradas de yt-dlp a nuestro formato estándar,

        respetando fielmente la ordenación y criterios naturales por defecto de yt-dlp.

        """

        if not entries:

            return []



        resultados = []

        is_music_search = (isinstance(query, str) and 'music.youtube.com' in query)

        for idx, entry in enumerate(entries[:max_results], start_index):

            if not entry:

                continue

            if not entry.get('title') and not entry.get('id'):

                continue

            item_id = entry.get('id', '')

            raw_title = entry.get('title') or entry.get('track') or 'Pista musical'

            titulo = limpiar_extension_titulo(raw_title)

            canal = entry.get('uploader') or entry.get('channel') or entry.get('artist') or entry.get('creator') or ''

            if (not canal or canal == 'Desconocido') and parent_channel_name:

                canal = parent_channel_name

            if not canal:

                canal = 'YouTube Music' if (is_music_search or 'music.youtube.com' in str(entry.get('url', ''))) else 'Desconocido'

            

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



            is_music_item = (
                is_music_search or
                'music.youtube.com' in url or
                (canal and (canal.strip().endswith(' - Topic') or canal.strip().endswith(' - Tema'))) or
                bool(entry.get('track')) or
                bool(entry.get('album'))
            )

            art_val = entry.get('artist') or entry.get('creator') or entry.get('uploader') or canal
            if art_val:
                art_val = re.sub(r'\s*-\s*(Topic|Tema)$', '', str(art_val)).strip()

            year_val = entry.get('release_year') or entry.get('year') or (str(entry.get('upload_date'))[:4] if entry.get('upload_date') and len(str(entry.get('upload_date'))) >= 4 else '')

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
                'is_music': is_music_item,
                'tipo_item': ('music' if is_music_item else tipo_item),
                'artist': art_val or '',
                'album': entry.get('album') or '',
                'year': str(year_val) if year_val else '',
                'track': entry.get('track') or '',
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

        last_error = ""



        if custom_exe:

                try:

                    ext_arg = get_ytdlp_extractor_args()

                    ext_args_cmd = ["--extractor-args", ext_arg] if ext_arg else []

                    cmd = [

                        custom_exe,

                        clean_url,

                        "--dump-single-json",

                        "--flat-playlist",

                        "--no-download",

                        "--no-warnings",

                        "--playlist-items", "0"

                    ] + ext_args_cmd

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

        }

        if get_ytdlp_clients_list():

            ydl_opts['extractor_args'] = {'youtube': {'player_client': get_ytdlp_clients_list()}}



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



        if search_type == 'music' and not (query.startswith('http://') or query.startswith('https://')):
            res_music = self._buscar_youtube_music_innertube(query, max_results=max_results, start_index=start_index)
            if res_music:
                return res_music

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

                elif search_type == 'music':

                    search_query = f"https://music.youtube.com/search?q={urllib.parse.quote_plus(query)}#songs"

                else:

                    # Búsqueda estándar de vídeos por defecto en yt-dlp

                    search_query = f"ytsearch{end_index}:{query}"

            else:

                search_prefix = engine if engine.endswith('search') else f"{engine}search"

                search_query = f"{search_prefix}{end_index}:{query}"



        # Si existe un yt-dlp.exe externo actualizado, se usa dinámicamente

        custom_exe = get_external_ytdlp_exe()

        last_error = ""

        if custom_exe:

                try:

                    ext_arg = get_ytdlp_extractor_args()

                    ext_args_cmd = ["--extractor-args", ext_arg] if ext_arg else []

                    cmd = [

                        custom_exe,

                        search_query,

                        "--dump-single-json",

                        "--flat-playlist",

                        "--no-download",

                        "--no-warnings",

                        "--playlist-items", f"{start_index}-{end_index}"

                    ] + ext_args_cmd

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



    def _extraer_channel_id(self, url_or_text: str) -> str:

        """Extrae o resuelve el ID canónico de canal (UC...) a partir de una URL o texto."""

        if not url_or_text:

            return ""

        s = url_or_text.strip()

        m = re.search(r'channel/(UC[a-zA-Z0-9_-]{22})', s)

        if m:

            return m.group(1)

        if s.startswith('UC') and len(s) == 24:

            return s

        if s.startswith('@'):

            s = f"https://www.youtube.com/{s}"

        elif not s.startswith(('http://', 'https://')):

            s = f"https://www.youtube.com/{s}"



        try:

            req = urllib.request.Request(s, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

            with urllib.request.urlopen(req, timeout=6) as resp:

                html = resp.read().decode('utf-8', errors='ignore')

                m2 = re.search(r'["\']channelId["\']\s*:\s*["\'](UC[a-zA-Z0-9_-]{22})["\']', html)

                if m2:

                    return m2.group(1)

                m3 = re.search(r'channel_id=(UC[a-zA-Z0-9_-]{22})', html)

                if m3:

                    return m3.group(1)

                m4 = re.search(r'<meta\s+itemprop=["\']channelId["\']\s+content=["\'](UC[a-zA-Z0-9_-]{22})["\']', html)

                if m4:

                    return m4.group(1)

        except Exception:

            pass

        return ""



    def _buscar_youtube_music_innertube(self, query: str, max_results: int = 25, start_index: int = 1):
        """
        Búsqueda especializada en YouTube Music usando la API Innertube WEB_REMIX.
        Obtiene de forma directa y nativa: título, artista, álbum, duración y visitas.
        Soporta continuaciones para entregar exactamente max_results y paginación continua.
        """
        try:
            needed = start_index + max_results - 1
            context = {
                "client": {
                    "clientName": "WEB_REMIX",
                    "clientVersion": "1.20231201.00.00",
                    "hl": "es",
                    "gl": "ES"
                }
            }

            def _extract_vid(raw_it):
                r_it = raw_it.get('musicResponsiveListItemRenderer', {})
                return (
                    r_it.get('playlistItemData', {}).get('videoId') or
                    r_it.get('overlay', {}).get('musicItemThumbnailOverlayRenderer', {}).get('content', {}).get('musicPlayButtonRenderer', {}).get('playNavigationEndpoint', {}).get('watchEndpoint', {}).get('videoId')
                )

            cache = getattr(self, '_music_search_cache', {}) or {}
            if cache.get('query') == query and start_index > 1:
                items_raw = cache.get('items_raw', [])
                continuation_token = cache.get('continuation_token')
                seen_ids = {_extract_vid(it) for it in items_raw if _extract_vid(it)}
            else:
                api_url = "https://music.youtube.com/youtubei/v1/search"
                body = {
                    "context": context,
                    "query": query,
                    "params": "EgWKAQIIAWoQEAMQBBAJEAoQBRAREBAQFQ%3D%3D"
                }
                req = urllib.request.Request(
                    api_url,
                    data=json.dumps(body).encode('utf-8'),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))

                sections = data.get('contents', {}).get('tabbedSearchResultsRenderer', {}).get('tabs', [{}])[0].get('tabRenderer', {}).get('content', {}).get('sectionListRenderer', {}).get('contents', [])
                items_raw = []
                seen_ids = set()
                continuation_token = None
                for s in sections:
                    shelf = s.get('musicShelfRenderer', {})
                    if shelf:
                        for it in shelf.get('contents', []):
                            vid = _extract_vid(it)
                            if vid and vid not in seen_ids:
                                seen_ids.add(vid)
                                items_raw.append(it)
                            elif not vid:
                                items_raw.append(it)
                        conts = shelf.get('continuations', [])
                        if conts:
                            continuation_token = conts[0].get('nextContinuationData', {}).get('continuation')

            while len(items_raw) < needed and continuation_token:
                try:
                    req_c = urllib.request.Request(
                        f"https://music.youtube.com/youtubei/v1/search?continuation={continuation_token}",
                        data=json.dumps({"context": context}).encode('utf-8'),
                        headers={
                            "Content-Type": "application/json",
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                        }
                    )
                    with urllib.request.urlopen(req_c, timeout=10) as resp_c:
                        data_c = json.loads(resp_c.read().decode('utf-8'))
                    c_shelf = data_c.get('continuationContents', {}).get('musicShelfContinuation', {})
                    new_items = c_shelf.get('contents', [])
                    if not new_items:
                        break
                    for it in new_items:
                        vid = _extract_vid(it)
                        if vid and vid not in seen_ids:
                            seen_ids.add(vid)
                            items_raw.append(it)
                        elif not vid:
                            items_raw.append(it)
                    conts = c_shelf.get('continuations', [])
                    continuation_token = conts[0].get('nextContinuationData', {}).get('continuation') if conts else None
                except Exception as e_c:
                    logger.warning(f"Error al obtener continuación de YouTube Music: {e_c}")
                    break

            self._music_search_cache = {
                'query': query,
                'items_raw': items_raw,
                'continuation_token': continuation_token
            }

            if not items_raw:
                return []

            resultados = []
            sliced = items_raw[start_index - 1 : needed]

            for idx, raw_item in enumerate(sliced, start=start_index):
                item = raw_item.get('musicResponsiveListItemRenderer', {})
                if not item:
                    continue

                video_id = (
                    item.get('playlistItemData', {}).get('videoId') or
                    item.get('overlay', {}).get('musicItemThumbnailOverlayRenderer', {}).get('content', {}).get('musicPlayButtonRenderer', {}).get('playNavigationEndpoint', {}).get('watchEndpoint', {}).get('videoId')
                )
                if not video_id:
                    continue

                flex_cols = item.get('flexColumns', [])
                titulo = ""
                if len(flex_cols) > 0:
                    runs0 = flex_cols[0].get('musicResponsiveListItemFlexColumnRenderer', {}).get('text', {}).get('runs', [])
                    if runs0:
                        titulo = runs0[0].get('text', '')

                artista = ""
                album = ""
                album_id = ""
                artist_id = ""
                duracion_str = "--:--"
                views_str = "--"

                if len(flex_cols) > 1:
                    runs1 = flex_cols[1].get('musicResponsiveListItemFlexColumnRenderer', {}).get('text', {}).get('runs', [])
                    for r_item in runs1:
                        b_endpoint = r_item.get('navigationEndpoint', {}).get('browseEndpoint', {})
                        page_type = (b_endpoint.get('browseEndpointContextSupportedConfigs', {})
                                     .get('browseEndpointContextMusicConfig', {})
                                     .get('pageType'))
                        bid = b_endpoint.get('browseId', '')
                        if page_type == 'MUSIC_PAGE_TYPE_ALBUM' or bid.startswith('MPREb_') or bid.startswith('OLAK5uy_'):
                            album_id = bid
                        elif page_type == 'MUSIC_PAGE_TYPE_ARTIST' or bid.startswith('UC'):
                            artist_id = bid

                    partes = [r.get('text', '').strip() for r in runs1 if r.get('text', '').strip() and r.get('text', '').strip() != '•']
                    if len(partes) >= 1:
                        artista = partes[0]
                    if len(partes) >= 2:
                        if re.match(r'^\d+:\d+', partes[-1]):
                            duracion_str = partes[-1]
                            if len(partes) >= 3:
                                album = partes[1]
                        else:
                            album = partes[1]
                    if len(partes) >= 3 and not album:
                        album = partes[1]

                year_str = ""
                for p in partes:
                    if re.match(r'^(19\d\d|20\d\d)$', p):
                        year_str = p
                        break

                if len(flex_cols) > 2:
                    runs2 = flex_cols[2].get('musicResponsiveListItemFlexColumnRenderer', {}).get('text', {}).get('runs', [])
                    if runs2:
                        views_str = runs2[0].get('text', '--')

                dur_secs = 0
                if ':' in duracion_str:
                    try:
                        p_dur = [int(x) for x in duracion_str.split(':')]
                        if len(p_dur) == 2:
                            dur_secs = p_dur[0] * 60 + p_dur[1]
                        elif len(p_dur) == 3:
                            dur_secs = p_dur[0] * 3600 + p_dur[1] * 60 + p_dur[2]
                    except Exception:
                        pass

                resultados.append({
                    'index': idx,
                    'id': video_id,
                    'title': titulo,
                    'channel': artista or 'YouTube Music',
                    'channel_url': f"https://music.youtube.com/watch?v={video_id}",
                    'duration_seconds': dur_secs,
                    'duration': duracion_str,
                    'views': views_str,
                    'view_count': 0,
                    'url': f"https://music.youtube.com/watch?v={video_id}",
                    'description': f"Artista: {artista}\nÁlbum: {album}",
                    'is_playlist': False,
                    'is_channel': False,
                    'is_music': True,
                    'tipo_item': 'music',
                    'artist': artista,
                    'album': album,
                    'album_id': album_id,
                    'artist_id': artist_id,
                    'year': year_str,
                    'track': titulo,
                    'selected': False,
                })

            return resultados
        except Exception:
            return []

    def buscar_album_canciones(self, album_id_or_name: str, album_title: str = "", artist_name: str = "", max_results: int = 50) -> list:
        """
        Obtiene la lista completa de canciones de un álbum en YouTube Music usando Innertube.
        Soporta browseId (MPREb_..., OLAK5uy_...), URLs de álbum/playlist, o búsqueda por nombre de álbum y artista.
        """
        browse_id = ""
        target = (album_id_or_name or "").strip()

        # 1. Si target ya es browseId o contiene OLAK / MPREb
        if target.startswith("MPREb_") or target.startswith("OLAK5uy_"):
            browse_id = target
        elif "list=" in target:
            m = re.search(r'list=([a-zA-Z0-9_-]+)', target)
            if m:
                browse_id = m.group(1)
        elif "music.youtube.com/browse/" in target:
            browse_id = target.split("music.youtube.com/browse/")[-1].split("?")[0]

        # 2. Si no tenemos browse_id, buscar el álbum por texto (artista + álbum)
        if not browse_id:
            query_lookup = f"{artist_name} {album_title or target}".strip()
            if query_lookup:
                try:
                    api_url = "https://music.youtube.com/youtubei/v1/search"
                    body = {
                        "context": {
                            "client": {
                                "clientName": "WEB_REMIX",
                                "clientVersion": "1.20231201.00.00",
                                "hl": "es",
                                "gl": "ES"
                            }
                        },
                        "query": query_lookup,
                        "params": "EgWKAQIBAWoQEAMQBBAJEAoQBRAREBAQFQ%3D%3D"
                    }
                    req = urllib.request.Request(
                        api_url,
                        data=json.dumps(body).encode('utf-8'),
                        headers={
                            "Content-Type": "application/json",
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                        }
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read().decode('utf-8'))

                    contents = data.get('contents', {}).get('tabbedSearchResultsRenderer', {}).get('tabs', [{}])[0].get('tabRenderer', {}).get('content', {}).get('sectionListRenderer', {}).get('contents', [])
                    for sec in contents:
                        for item in sec.get('itemSectionRenderer', {}).get('contents', []):
                            nav = item.get('musicResponsiveListItemRenderer', {}).get('navigationEndpoint', {})
                            bid = nav.get('browseEndpoint', {}).get('browseId')
                            ptype = (nav.get('browseEndpoint', {})
                                     .get('browseEndpointContextSupportedConfigs', {})
                                     .get('browseEndpointContextMusicConfig', {})
                                     .get('pageType'))
                            if bid and (bid.startswith('MPREb_') or bid.startswith('OLAK5uy_') or ptype == 'MUSIC_PAGE_TYPE_ALBUM'):
                                browse_id = bid
                                break
                        if browse_id:
                            break
                        for item in sec.get('musicShelfRenderer', {}).get('contents', []):
                            nav = item.get('musicResponsiveListItemRenderer', {}).get('navigationEndpoint', {})
                            bid = nav.get('browseEndpoint', {}).get('browseId')
                            if bid and (bid.startswith('MPREb_') or bid.startswith('OLAK5uy_')):
                                browse_id = bid
                                break
                        if browse_id:
                            break
                except Exception as e:
                    logger.warning(f"Error en búsqueda previa de browseId de álbum: {e}")

        # Si aún no tenemos browse_id, fallback a búsqueda de canciones estándar con query
        if not browse_id:
            query_fallback = f"{artist_name} {album_title or target}".strip()
            return self._buscar_youtube_music_innertube(query_fallback, max_results=max_results, start_index=1)

        # 3. Navegar el álbum usando /youtubei/v1/browse
        try:
            api_url = "https://music.youtube.com/youtubei/v1/browse"
            body = {
                "context": {
                    "client": {
                        "clientName": "WEB_REMIX",
                        "clientVersion": "1.20231201.00.00",
                        "hl": "es",
                        "gl": "ES"
                    }
                },
                "browseId": browse_id
            }
            req = urllib.request.Request(
                api_url,
                data=json.dumps(body).encode('utf-8'),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            nombre_album = album_title or ""
            artista_album = artist_name or ""
            year_album = ""

            two_col = data.get('contents', {}).get('twoColumnBrowseResultsRenderer', {})
            tabs = two_col.get('tabs', [])
            if not tabs:
                tabs = data.get('contents', {}).get('singleColumnBrowseResultsRenderer', {}).get('tabs', [])
            if tabs:
                s_contents = tabs[0].get('tabRenderer', {}).get('content', {}).get('sectionListRenderer', {}).get('contents', [])
                for sc in s_contents:
                    hdr = sc.get('musicResponsiveHeaderRenderer')
                    if hdr:
                        if not nombre_album:
                            nombre_album = hdr.get('title', {}).get('runs', [{}])[0].get('text', '')
                        if not artista_album:
                            st_runs = hdr.get('straplineTextOne', {}).get('runs', [])
                            if st_runs:
                                artista_album = st_runs[0].get('text', '')
                        sub_runs = hdr.get('subtitle', {}).get('runs', [])
                        for sr in sub_runs:
                            stxt = sr.get('text', '').strip()
                            if re.match(r'^(19\d\d|20\d\d)$', stxt):
                                year_album = stxt
                                break
                        break

            mf = data.get('microformat', {}).get('microformatDataRenderer', {})
            if not nombre_album:
                nombre_album = mf.get('title', '')
            if not artista_album:
                desc = mf.get('description', '')
                if '•' in desc:
                    artista_album = desc.split('•')[-1].strip()

            self.last_container_title = nombre_album

            sections = two_col.get('secondaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
            items_raw = []
            for s in sections:
                shelf = s.get('musicShelfRenderer')
                if shelf:
                    items_raw.extend(shelf.get('contents', []))

            if not items_raw and tabs:
                for s in tabs[0].get('tabRenderer', {}).get('content', {}).get('sectionListRenderer', {}).get('contents', []):
                    shelf = s.get('musicShelfRenderer')
                    if shelf:
                        items_raw.extend(shelf.get('contents', []))

            resultados = []
            for idx, raw_item in enumerate(items_raw[:max_results], start=1):
                item = raw_item.get('musicResponsiveListItemRenderer')
                if not item:
                    continue

                video_id = (
                    item.get('playlistItemData', {}).get('videoId') or
                    item.get('overlay', {}).get('musicItemThumbnailOverlayRenderer', {}).get('content', {}).get('musicPlayButtonRenderer', {}).get('playNavigationEndpoint', {}).get('watchEndpoint', {}).get('videoId')
                )
                if not video_id:
                    continue

                flex_cols = item.get('flexColumns', [])
                titulo = ""
                if len(flex_cols) > 0:
                    runs0 = flex_cols[0].get('musicResponsiveListItemFlexColumnRenderer', {}).get('text', {}).get('runs', [])
                    if runs0:
                        titulo = runs0[0].get('text', '')

                artista_track = artista_album
                if len(flex_cols) > 1:
                    runs1 = flex_cols[1].get('musicResponsiveListItemFlexColumnRenderer', {}).get('text', {}).get('runs', [])
                    p_track = [r.get('text', '').strip() for r in runs1 if r.get('text', '').strip() and r.get('text', '').strip() != '•']
                    if p_track and p_track[0]:
                        artista_track = p_track[0]

                duracion_str = "--:--"
                fixed = item.get('fixedColumns', [])
                if fixed:
                    runs_f = fixed[0].get('musicResponsiveListItemFixedColumnRenderer', {}).get('text', {}).get('runs', [])
                    if runs_f:
                        duracion_str = runs_f[0].get('text', '--:--')

                dur_secs = 0
                if ':' in duracion_str:
                    try:
                        p_dur = [int(x) for x in duracion_str.split(':')]
                        if len(p_dur) == 2:
                            dur_secs = p_dur[0] * 60 + p_dur[1]
                        elif len(p_dur) == 3:
                            dur_secs = p_dur[0] * 3600 + p_dur[1] * 60 + p_dur[2]
                    except Exception:
                        pass

                views_str = "--"
                if len(flex_cols) > 2:
                    runs2 = flex_cols[2].get('musicResponsiveListItemFlexColumnRenderer', {}).get('text', {}).get('runs', [])
                    if runs2:
                        views_str = runs2[0].get('text', '--')

                track_num = item.get('index', {}).get('runs', [{}])[0].get('text', str(idx))

                resultados.append({
                    'index': idx,
                    'track_number': track_num,
                    'id': video_id,
                    'title': titulo,
                    'channel': artista_track or artista_album or 'YouTube Music',
                    'channel_url': f"https://music.youtube.com/watch?v={video_id}",
                    'duration_seconds': dur_secs,
                    'duration': duracion_str,
                    'views': views_str,
                    'view_count': 0,
                    'url': f"https://music.youtube.com/watch?v={video_id}",
                    'description': f"Artista: {artista_track}\nÁlbum: {nombre_album}",
                    'is_playlist': False,
                    'is_channel': False,
                    'is_music': True,
                    'tipo_item': 'music',
                    'artist': artista_track,
                    'album': nombre_album,
                    'album_id': browse_id,
                    'year': year_album,
                    'track': titulo,
                    'selected': False,
                })

            return resultados
        except Exception as e:
            logger.warning(f"Error al obtener canciones del álbum {browse_id}: {e}")
            query_fallback = f"{artist_name} {album_title or target}".strip()
            return self._buscar_youtube_music_innertube(query_fallback, max_results=max_results, start_index=1)

    def _extraer_videos_canal_musica(self, channel_url_or_base: str, max_results: int = 25, start_index: int = 1, channel_title: str = ''):

        """Fallback para canales de música / 'Topic' sin pestaña /videos usando Innertube de YouTube Music."""

        try:

            channel_id = self._extraer_channel_id(channel_url_or_base)

            if not channel_id:

                return []



            api_url = "https://www.youtube.com/youtubei/v1/browse?prettyPrint=false"

            body = {

                "context": {

                    "client": {

                        "clientName": "WEB_REMIX",

                        "clientVersion": "1.20231201.00.00",

                        "hl": "es",

                        "gl": "ES"

                    }

                },

                "browseId": channel_id

            }

            headers = {

                "Content-Type": "application/json",

                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

            }

            req = urllib.request.Request(api_url, data=json.dumps(body).encode('utf-8'), headers=headers)

            with urllib.request.urlopen(req, timeout=8) as resp:

                text = resp.read().decode('utf-8')

                data = json.loads(text)



            artist_name = ""

            try:

                runs = data.get('header', {}).get('musicImmersiveHeaderRenderer', {}).get('title', {}).get('runs', [])

                if not runs:

                    runs = data.get('header', {}).get('musicVisualHeaderRenderer', {}).get('title', {}).get('runs', [])

                if runs:

                    artist_name = runs[0].get('text', '')

            except Exception:

                pass



            playlists = []

            # 1. Buscar bottomEndpoint en la estantería de canciones principales (Top songs)

            try:

                sections = data.get('contents', {}).get('singleColumnBrowseResultsRenderer', {}).get('tabs', [])[0].get('tabRenderer', {}).get('content', {}).get('sectionListRenderer', {}).get('contents', [])

                for sec in sections:

                    shelf = sec.get('musicShelfRenderer')

                    if shelf:

                        b_id = shelf.get('bottomEndpoint', {}).get('browseEndpoint', {}).get('browseId', '')

                        if b_id:

                            pl = b_id[2:] if b_id.startswith('VL') else b_id

                            if pl.startswith('OLAK5uy_') and pl not in playlists:

                                playlists.append(pl)

            except Exception:

                pass



            # 2. Buscar cualquier otra playlist de tipo OLAK5uy_ (álbumes, sencillos, etc.)

            for m in re.finditer(r'"browseId"\s*:\s*"(?:VL)?(OLAK5uy_[^"]+)"', text):

                pl = m.group(1)

                if pl not in playlists:

                    playlists.append(pl)



            for pl_id in playlists:

                pl_url = f"https://www.youtube.com/playlist?list={pl_id}"

                try:

                    res = self._extraer_flat_url(pl_url, max_results=max_results, is_playlist_list=False, start_index=start_index, parent_channel_name=artist_name or channel_title)

                    if res:

                        if artist_name and not getattr(self, 'last_container_title', None):

                            self.last_container_title = f"{artist_name} - Topic"

                        return res

                except Exception:

                    continue

        except Exception:

            pass



        return []



    def buscar_canal_videos(self, channel_url: str, max_results: int = 25, start_index: int = 1, channel_title: str = ''):

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

            res = self._extraer_flat_url(url_final, max_results=max_results, is_playlist_list=False, query=channel_url, start_index=start_index, parent_channel_name=channel_title)

            if res:

                return res

        except Exception as e:

            # Si el canal no tiene pestaña '/videos' (canales temáticos de música tipo 'Topic', directos o perfiles sin subidas directas),

            # reintentamos con la URL base del canal donde yt-dlp redirige a las pistas/subidas si existen.

            try:

                res_base = self._extraer_flat_url(base, max_results=max_results, is_playlist_list=False, query=channel_url, start_index=start_index, parent_channel_name=channel_title)

                if res_base:

                    return res_base

            except Exception:

                pass



            # Si yt-dlp tampoco encuentra subidas directas (frecuente en canales 'Topic' de YouTube Music),

            # recurrimos a YouTube Music Innertube para obtener las canciones o álbumes del artista.

            res_music = self._extraer_videos_canal_musica(base, max_results=max_results, start_index=start_index, channel_title=channel_title)

            if res_music:

                return res_music



            err_msg = str(e).lower()

            if "does not have a videos tab" in err_msg or "this channel does not have a" in err_msg:

                return []

            raise e



        # Si url_final no arrojó excepción pero devolvió lista vacía en la primera página,

        # probamos con la URL base del canal y luego con YouTube Music

        if start_index == 1:

            try:

                res_base = self._extraer_flat_url(base, max_results=max_results, is_playlist_list=False, query=channel_url, start_index=start_index, parent_channel_name=channel_title)

                if res_base:

                    return res_base

            except Exception:

                pass



            res_music = self._extraer_videos_canal_musica(base, max_results=max_results, start_index=start_index, channel_title=channel_title)

            if res_music:

                return res_music



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



    def _extraer_flat_url(self, target_url: str, max_results: int = 50, is_playlist_list: bool = False, query: str = '', start_index: int = 1, parent_channel_name: str = ''):

        """Método unificado para extraer entradas usando CLI externa o librería interna con paginación."""

        end_index = max(start_index, start_index + max_results - 1)

        custom_exe = get_external_ytdlp_exe()

        last_error = ""

        if custom_exe:

                try:

                    ext_arg = get_ytdlp_extractor_args()

                    ext_args_cmd = ["--extractor-args", ext_arg] if ext_arg else []

                    cmd = [

                        custom_exe,

                        target_url,

                        "--dump-single-json",

                        "--flat-playlist",

                        "--no-download",

                        "--no-warnings",

                        "--playlist-items", f"{start_index}-{end_index}"

                    ] + ext_args_cmd

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

                        is_container = (

                            info.get('_type') in ('playlist', 'channel') or

                            '/channel/' in target_url or

                            '/playlist' in target_url or

                            '/@' in target_url or

                            '/c/' in target_url or

                            '/user/' in target_url

                        )

                        if not entries and info.get('title') and not is_playlist_list and not is_container:

                            entries = [info]

                        raw_parent_ch = info.get('channel') or info.get('uploader') or parent_channel_name or ''

                        if not raw_parent_ch and info.get('title') and not is_playlist_list:

                            clean_t = re.sub(r'\s*-\s*(?:Videos|Uploads|Vídeos|Pistas|Playlists|Listas)$', '', info.get('title', ''), flags=re.IGNORECASE).strip()

                            if clean_t:

                                raw_parent_ch = clean_t

                        self.last_container_title = raw_parent_ch or info.get('title') or ''

                        parent_ch = info.get('uploader_url') or info.get('channel_url') or ''

                        return self._procesar_entries(entries, max_results=max_results, is_playlist_list=is_playlist_list, query=query, start_index=start_index, parent_channel_url=parent_ch, parent_channel_name=raw_parent_ch)

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

        }

        if get_ytdlp_clients_list():

            ydl_opts['extractor_args'] = {'youtube': {'player_client': get_ytdlp_clients_list()}}



        yt_dlp = _ensure_ytdlp()

        if yt_dlp:

            try:

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                    info = ydl.extract_info(target_url, download=False)

                    self.last_container_title = info.get('title') or ''

                    entries = list(info.get('entries') or [])

                    is_container = (

                        info.get('_type') in ('playlist', 'channel') or

                        '/channel/' in target_url or

                        '/playlist' in target_url or

                        '/@' in target_url or

                        '/c/' in target_url or

                        '/user/' in target_url

                    )

                    if not entries and info.get('title') and not is_playlist_list and not is_container:

                        entries = [info]

                    raw_parent_ch = info.get('channel') or info.get('uploader') or parent_channel_name or ''

                    if not raw_parent_ch and info.get('title') and not is_playlist_list:

                        clean_t = re.sub(r'\s*-\s*(?:Videos|Uploads|Vídeos|Pistas|Playlists|Listas)$', '', info.get('title', ''), flags=re.IGNORECASE).strip()

                        if clean_t:

                            raw_parent_ch = clean_t

                    self.last_container_title = raw_parent_ch or info.get('title') or ''

                    parent_ch = info.get('uploader_url') or info.get('channel_url') or ''

                    return self._procesar_entries(entries, max_results=max_results, is_playlist_list=is_playlist_list, query=query, start_index=start_index, parent_channel_url=parent_ch, parent_channel_name=raw_parent_ch)

            except Exception as e:

                last_error = str(e)



        if not custom_exe and not yt_dlp:

            raise RuntimeError("No se encuentra la librería necesaria (yt-dlp.exe) para la ejecución del programa.")



        if last_error:

            raise RuntimeError(last_error)

        return []



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

            try:

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                    info = ydl.extract_info(target_url, download=False)

                    if isinstance(info, dict):

                        return info.get('description') or ""

            except Exception:

                pass

        return ""

