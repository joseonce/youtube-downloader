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
import urllib.request

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



from downloader_search import (
    YouTubeSearchMixin,
    get_ytdlp_extractor_args,
    get_ytdlp_clients_list
)


class YouTubeDownloader(YouTubeSearchMixin):
    def __init__(self):
        self._cancel_requested = False
        self._metodo_override = None
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

    def descargar(self, url: str, formato: str, destino: str,
                  on_progress=None, on_finished=None, on_error=None,
                  metodo_override=None):
        """
        Descarga un vídeo o audio de YouTube en un hilo secundario.
        Aplica inmediatamente el motor yt-dlp actualizado si existe.
        """
        self._cancel_requested = False
        if metodo_override is not None:
            self._metodo_override = metodo_override

        def _worker():
            custom_exe = get_external_ytdlp_exe()
            cfg = getattr(self, 'config', None) or cargar_configuracion()
            last_download_error = ""

            # --- SI HAY UN MOTOR EXTERNO ACTUALIZADO A NIGHTLY ---
            if custom_exe:
                try:
                    outtmpl = os.path.join(destino, '%(title)s.%(ext)s')
                    from config_manager import get_ytdlp_extractor_args, get_ytdlp_clients_list
                    ext_arg = get_ytdlp_extractor_args(override=getattr(self, '_metodo_override', None))
                    base_args = [
                        custom_exe,
                        url,
                        "--output", outtmpl,
                        "--newline",
                        "--no-warnings",
                        "--replace-in-metadata", "title", r"(?i)\.(mp4|flv|mkv|webm|avi|wmv|mov|m4v|3gp|vob|ogv|divx|mp3|m4a|aac|wav|flac|ogg|opus|wma)$", ""
                    ]
                    if ext_arg:
                        base_args.extend(["--extractor-args", ext_arg])

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

    @staticmethod
    def _limpiar_linea_transcripcion(linea: str) -> str:
        """
        Limpia signos musicales ([♪♪♪], ♪, ♫), etiquetas no vocales ([Música], [Aplausos])
        y espacios extra, preservando la marca de tiempo inicial si existe.
        """
        if not linea:
            return ""

        m_tiempo = re.match(r'^(\[\d{1,2}:\d{2}(?::\d{2})?\])\s*', linea)
        prefix = ""
        texto = linea
        if m_tiempo:
            prefix = m_tiempo.group(1) + " "
            texto = linea[m_tiempo.end():]

        # 1. Eliminar corchetes o paréntesis que contengan notas musicales
        texto = re.sub(r'\[[\s♪♫♩♬♭♮♯\-_.~]+\]', '', texto)
        texto = re.sub(r'\([\s♪♫♩♬♭♮♯\-_.~]+\)', '', texto)
        # 2. Eliminar caracteres de notas musicales sueltos
        texto = re.sub(r'[♪♫♩♬♭♮♯]+', '', texto)
        # 3. Eliminar etiquetas no vocales comunes
        patron_etiquetas = (
            r'[\[\(]\s*(?:'
            r'm[uú]sica(?:\s+de\s+fondo)?|music(?:\s+playing)?|background\s+music|'
            r'aplausos|applause|risas|laughter|chuckle|gasp|sigh|suspiros|'
            r'silencio|silence|gritos|screams|acordes|canto|singing'
            r')\s*[\]\)]'
        )
        texto = re.sub(patron_etiquetas, '', texto, flags=re.IGNORECASE)
        # 4. Normalizar espacios y signos de puntuación huérfanos
        texto = re.sub(r'\s+', ' ', texto).strip()
        texto = re.sub(r'\s+([.,;:!?])', r'\1', texto)
        texto = re.sub(r'^[\s,;:\-_~]+|[\s\-_~]+$', '', texto).strip()

        if not texto:
            return ""
        return f"{prefix}{texto}" if prefix else texto

    def _procesar_json3_transcripcion(self, data: dict, con_marcas: bool = False) -> str:
        """Procesa datos de subtítulos en formato json3 y genera texto separado por líneas (con o sin marcas)."""
        events = data.get('events', [])
        lineas = []
        last_clean = ""

        for ev in events:
            segs = ev.get('segs', [])
            if not segs:
                continue
            texto = "".join(s.get('utf8', '') for s in segs)
            texto = re.sub(r'[\r\n]+', ' ', texto)
            texto = re.sub(r'\s+', ' ', texto).strip()
            if not texto:
                continue

            limpio = self._limpiar_linea_transcripcion(texto)
            if not limpio or limpio == last_clean:
                continue

            if con_marcas:
                t_ms = ev.get('tStartMs', 0)
                secs = int(t_ms / 1000)
                mins = int(secs / 60)
                rem_secs = secs % 60
                hrs = int(mins / 60)
                rem_mins = mins % 60

                if hrs > 0:
                    time_tag = f"[{hrs:02d}:{rem_mins:02d}:{rem_secs:02d}]"
                else:
                    time_tag = f"[{rem_mins:02d}:{rem_secs:02d}]"
                lineas.append(f"{time_tag} {limpio}")
            else:
                lineas.append(limpio)

            last_clean = limpio

        return "\n".join(lineas)

    def _procesar_vtt_transcripcion(self, content: str, con_marcas: bool = False) -> str:
        """Procesa subtítulos en formato WebVTT y genera texto separado por líneas (con o sin marcas)."""
        time_pattern = re.compile(r'(\d{2}:\d{2}(?::\d{2})?(?:\.\d{3})?)\s*-->\s*(\d{2}:\d{2}(?::\d{2})?(?:\.\d{3})?)')
        blocks = re.split(r'\n\s*\n', content)
        output_lines = []
        last_clean = ""

        for block in blocks:
            block = block.strip()
            if not block or block.startswith('WEBVTT') or block.startswith('Kind:') or block.startswith('Language:'):
                continue

            lines = block.splitlines()
            time_match = None
            text_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                tm = time_pattern.search(line)
                if tm:
                    time_match = tm
                elif not time_match:
                    continue
                else:
                    cleaned = re.sub(r'<[^>]+>', '', line).strip()
                    cleaned = re.sub(r'&nbsp;', ' ', cleaned)
                    cleaned = re.sub(r'&#39;', "'", cleaned)
                    cleaned = re.sub(r'&quot;', '"', cleaned)
                    cleaned = re.sub(r'&amp;', '&', cleaned)
                    if cleaned:
                        text_lines.append(cleaned)

            if not text_lines:
                continue

            full_block_text = " ".join(text_lines).strip()
            # En VTT acumulativo (rolling subtitles), descartar prefijos repetidos
            if last_clean and full_block_text.startswith(last_clean):
                texto_segmento = full_block_text[len(last_clean):].strip()
            else:
                texto_segmento = full_block_text

            limpio = self._limpiar_linea_transcripcion(texto_segmento)
            if not limpio or limpio == last_clean:
                continue

            if time_match:
                start_t = time_match.group(1).split('.')[0]
                if start_t.startswith('00:'):
                    start_t = start_t[3:]
            else:
                start_t = ""

            if con_marcas:
                output_lines.append(f"[{start_t}] {limpio}")
            else:
                output_lines.append(limpio)

            last_clean = limpio

        return "\n".join(output_lines)

    def _traducir_texto_transcripcion(self, texto: str, target_lang: str) -> str:
        """
        Traduce el texto de transcripción al idioma destino por lotes usando el endpoint de Google Translate.
        Preserva saltos de línea y marcas de tiempo [mm:ss].
        """
        if not texto or not texto.strip():
            return texto

        target_lang = target_lang.lower().strip()
        lineas = texto.splitlines()
        if not lineas:
            return texto

        lineas_traducidas = []
        chunk = []
        chunk_len = 0

        def _procesar_lote(lote_lineas):
            if not lote_lineas:
                return []
            raw_text = "\n".join(lote_lineas)
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t"
            data = urllib.parse.urlencode({'q': raw_text}).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data_json = json.loads(resp.read().decode('utf-8'))
                res_bloques = data_json[0] if data_json and isinstance(data_json, list) else []
                traduccion = "".join(s[0] for s in res_bloques if s and isinstance(s, list) and s[0])
                return traduccion.splitlines()

        for linea in lineas:
            if chunk_len + len(linea) > 2500 and chunk:
                try:
                    lineas_traducidas.extend(_procesar_lote(chunk))
                except Exception:
                    lineas_traducidas.extend(chunk)
                chunk = []
                chunk_len = 0
            chunk.append(linea)
            chunk_len += len(linea)

        if chunk:
            try:
                lineas_traducidas.extend(_procesar_lote(chunk))
            except Exception:
                lineas_traducidas.extend(chunk)

        return "\n".join(lineas_traducidas)

    def extraer_transcripcion(self, url_o_id: str, idioma: str = 'orig', con_marcas: bool = False) -> str:
        """
        Extrae la transcripción o subtítulos de un vídeo a texto plano.
        - idioma: 'orig' (idioma original del vídeo) o código ISO ('es', 'en', 'fr', etc.).
        - con_marcas: True incluye marcas de tiempo [mm:ss], False texto continuo limpio separado por líneas.
        """
        if not url_o_id:
            raise ValueError("URL o identificador de vídeo no válido.")

        url = url_o_id.strip()
        if not url.startswith(('http://', 'https://')):
            url = f"https://www.youtube.com/watch?v={url}"

        custom_exe = get_external_ytdlp_exe()
        info = None

        if custom_exe:
            try:
                cmd = [custom_exe, url, "--dump-single-json", "--skip-download", "--no-warnings"]
                ext_arg = get_ytdlp_extractor_args()
                if ext_arg:
                    cmd += ["--extractor-args", ext_arg]
                res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20)
                if res.returncode == 0 and res.stdout.strip():
                    info = json.loads(res.stdout)
            except Exception:
                pass

        yt_dlp_lib = _ensure_ytdlp()
        if not info and yt_dlp_lib:
            yt_dlp = yt_dlp_lib
            try:
                ydl_opts = {'quiet': True, 'skip_download': True}
                ext_arg = get_ytdlp_extractor_args()
                if ext_arg:
                    ydl_opts['extractor_args'] = {'youtube': {'player_client': get_ytdlp_clients_list()}}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception:
                pass

        if not info:
            raise RuntimeError("No se pudo obtener información del vídeo para extraer la transcripción.")

        subs = info.get('subtitles') or {}
        auto = info.get('automatic_captions') or {}

        if not subs and not auto:
            raise RuntimeError("Este vídeo no dispone de subtítulos ni transcripción disponibles en YouTube.")

        # Determinar el idioma original del vídeo
        orig_lang = None
        if info.get('language'):
            orig_lang = info.get('language')
        if not orig_lang:
            for k in list(auto.keys()) + list(subs.keys()):
                if k.endswith('-orig'):
                    orig_lang = k.replace('-orig', '')
                    break
        if not orig_lang and subs:
            orig_lang = list(subs.keys())[0]
        if not orig_lang and auto:
            orig_lang = list(auto.keys())[0]
        if not orig_lang:
            orig_lang = 'es'

        idioma_pedido = (idioma or 'orig').strip().lower()
        necesita_traduccion = idioma_pedido not in ('orig', 'original') and idioma_pedido != orig_lang.lower()
        target_lang = idioma_pedido if necesita_traduccion else orig_lang

        def _buscar_track(idioma_codigo, permitir_auto=True):
            contenedores = [subs]
            if permitir_auto:
                contenedores.append(auto)
            for container in contenedores:
                fmts = container.get(idioma_codigo)
                if not fmts:
                    for k, v in container.items():
                        if k == idioma_codigo or k.startswith(f"{idioma_codigo}-"):
                            fmts = v
                            break
                if fmts:
                    for f in fmts:
                        if f.get('ext') == 'json3':
                            return f.get('url'), 'json3'
                    for f in fmts:
                        if f.get('ext') == 'vtt':
                            return f.get('url'), 'vtt'
            return None, None

        # Si se pidió traducción:
        # 1. Comprobar si hay un subtítulo humano en subs para ese idioma que no use traducción automática de YouTube (&tlang=)
        track_url = None
        track_ext = None
        descargar_traducido_directo = False

        if necesita_traduccion:
            track_url, track_ext = _buscar_track(target_lang, permitir_auto=False)
            if track_url and 'tlang=' not in track_url:
                descargar_traducido_directo = True

        if not descargar_traducido_directo:
            # Buscar el track en el idioma original (primero subs humanos, luego auto)
            track_url, track_ext = _buscar_track(orig_lang, permitir_auto=True)
            if not track_url:
                primera_clave = (list(subs.keys()) or list(auto.keys()))[0]
                track_url, track_ext = _buscar_track(primera_clave, permitir_auto=True)

        if not track_url:
            raise RuntimeError("No se encontró transcripción ni subtítulos disponibles para este vídeo.")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        req = urllib.request.Request(track_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode('utf-8')

        if track_ext == 'json3':
            data = json.loads(content)
            texto_extraido = self._procesar_json3_transcripcion(data, con_marcas=con_marcas)
        else:
            texto_extraido = self._procesar_vtt_transcripcion(content, con_marcas=con_marcas)

        # Si el usuario solicitó traducción a otro idioma y se extrajo el original, traducirlo de forma transparente
        if necesita_traduccion and not descargar_traducido_directo:
            texto_extraido = self._traducir_texto_transcripcion(texto_extraido, target_lang=target_lang)

        return texto_extraido

    def descargar_transcripcion(self, item_o_url, destino_dir: str, idioma: str = 'orig', con_marcas: bool = False) -> str:
        """
        Descarga la transcripción de un vídeo y la guarda como archivo .txt.
        Retorna la ruta absoluta del archivo generado.
        """
        if isinstance(item_o_url, dict):
            url = item_o_url.get('url') or item_o_url.get('id', '')
            titulo = item_o_url.get('title', 'Transcripcion')
        else:
            url = str(item_o_url)
            titulo = 'Transcripcion'

        texto = self.extraer_transcripcion(url, idioma=idioma, con_marcas=con_marcas)
        if not texto or not texto.strip():
            raise RuntimeError("La transcripción extraída está vacía.")

        if not os.path.exists(destino_dir):
            os.makedirs(destino_dir, exist_ok=True)

        nombre_base = limpiar_extension_titulo(titulo)
        nombre_base = re.sub(r'[\\/*?:"<>|]', '_', nombre_base).strip().rstrip('. ')
        if not nombre_base:
            nombre_base = "Transcripcion"

        sufijo_marcas = " (con marcas)" if con_marcas else ""
        sufijo_idioma = f" [{idioma}]" if idioma not in ('orig', 'original') else ""
        nombre_archivo = f"{nombre_base}{sufijo_idioma}{sufijo_marcas}.txt"
        ruta_archivo = os.path.join(destino_dir, nombre_archivo)

        contador = 1
        while os.path.exists(ruta_archivo):
            nombre_archivo = f"{nombre_base}{sufijo_idioma}{sufijo_marcas} ({contador}).txt"
            ruta_archivo = os.path.join(destino_dir, nombre_archivo)
            contador += 1

        with open(ruta_archivo, 'w', encoding='utf-8-sig') as f:
            f.write(texto)

        return ruta_archivo
