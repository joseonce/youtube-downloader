"""
Módulo de integración con libmpv (python-mpv), dispositivos de audio del sistema y notificaciones.
"""

import datetime
import os
import sys
import threading
import traceback
import wx
import wx.adv

import accessibility
import sound_manager
from config_manager import get_base_dir, cargar_configuracion, get_external_ytdlp_exe, get_config_dir

_mpv_initialized = False
_mpv_module = None
_playback_log_lock = threading.Lock()


def get_playback_log_path():
    """Retorna la ruta al archivo reproductor.log."""
    return os.path.join(get_config_dir(), 'reproductor.log')


def get_mpv_log_path():
    """Retorna la ruta al archivo mpv.log."""
    return os.path.join(get_config_dir(), 'mpv.log')


def log_playback(msg: str, level: str = "INFO", exc: Exception = None):
    """
    Registra un mensaje de diagnóstico detallado en config/reproductor.log.
    Incluye marca de tiempo, nivel, hilo y traza de error en caso de existir.
    """
    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        thread_name = threading.current_thread().name
        line = f"[{now_str}] [{level}] [{thread_name}] {msg}\n"
        if exc is not None:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            line += f"{tb}\n"

        log_path = get_playback_log_path()
        with _playback_log_lock:
            # Control de tamaño máximo (2 MB)
            try:
                if os.path.isfile(log_path) and os.path.getsize(log_path) > 2 * 1024 * 1024:
                    with open(log_path, 'r', encoding='utf-8', errors='replace') as rf:
                        tail_content = rf.readlines()[-2000:]
                    with open(log_path, 'w', encoding='utf-8', errors='replace') as wf:
                        wf.write("--- Log rotado automáticamente por tamaño ---\n")
                        wf.writelines(tail_content)
            except Exception:
                pass

            with open(log_path, 'a', encoding='utf-8', errors='replace') as f:
                f.write(line)
    except Exception:
        pass


def _ensure_c_numeric_locale():
    try:
        import locale
        locale.setlocale(locale.LC_NUMERIC, 'C')
    except Exception:
        pass
    try:
        import ctypes
        ctypes.cdll.msvcrt.setlocale(4, b'C')
    except Exception:
        pass


def init_mpv_env():
    """Localiza y configura la librería nativa mpv-2.dll / libmpv-2.dll en Windows."""
    global _mpv_initialized
    _ensure_c_numeric_locale()
    if _mpv_initialized:
        return
    base_dir = get_base_dir()
    meipass = getattr(sys, '_MEIPASS', None)

    candidates = []
    if meipass:
        candidates.extend([
            os.path.join(meipass, 'resources', 'mpv'),
            os.path.join(meipass, 'resources'),
            meipass
        ])
    candidates.extend([
        os.path.join(base_dir, 'resources', 'mpv'),
        os.path.join(base_dir, 'resources'),
        os.path.join(base_dir, 'mpv'),
        os.path.join(base_dir, 'YouTubeDownloader', 'resources', 'mpv'),
        os.path.join(os.path.dirname(base_dir), 'resources', 'mpv'),
        os.path.join(os.path.dirname(base_dir), 'YouTubeDownloader', 'resources', 'mpv'),
        r"C:\portables\YouTubeDownloader\resources\mpv",
        r"C:\portable\YouTubeDownloader\resources\mpv",
        r"C:\portable\resources\mpv",
    ])

    for p in candidates:
        if not os.path.exists(p):
            continue
        dll_2 = os.path.join(p, 'mpv-2.dll')
        dll_lib = os.path.join(p, 'libmpv-2.dll')
        dll_1 = os.path.join(p, 'mpv-1.dll')
        if os.path.isfile(dll_2) or os.path.isfile(dll_lib) or os.path.isfile(dll_1):
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(p)
                except Exception:
                    pass
            os.environ['PATH'] = p + os.pathsep + os.environ.get('PATH', '')
            break

    _mpv_initialized = True


def get_mpv_module():
    """Retorna el módulo mpv importado correctamente o None si no está disponible."""
    global _mpv_module
    if _mpv_module is not None:
        return _mpv_module
    init_mpv_env()
    try:
        import mpv as _m
        _mpv_module = _m
    except Exception:
        _mpv_module = None
    return _mpv_module


def resolve_mpv_audio_device(dev_id, player=None):
    """
    Resuelve y normaliza el identificador del dispositivo de salida de audio para libmpv.
    Soporta migración transparente desde GUIDs heredados de VLC ({0.0.0.00000000}.{...}).
    Si el dispositivo especificado no existe o es inválido, retorna 'auto' para garantizar
    que siempre haya salida de sonido por el dispositivo predeterminado del sistema.
    """
    if not dev_id or str(dev_id).strip() in ('', 'auto', 'default'):
        return 'auto'
    dev_str = str(dev_id).strip()

    device_list = []
    if player and hasattr(player, 'audio_device_list'):
        try:
            device_list = getattr(player, 'audio_device_list', []) or []
        except Exception:
            pass
    if not device_list:
        try:
            mpv_mod = get_mpv_module()
            if mpv_mod:
                _temp = mpv_mod.MPV(hwdec='no', osc=False, ytdl=False)
                device_list = getattr(_temp, 'audio_device_list', []) or []
                _temp.terminate()
        except Exception:
            pass

    valid_names = [d.get('name') for d in device_list if d.get('name')]

    # 1. Coincidencia exacta con nombre mpv
    if dev_str in valid_names:
        return dev_str

    # 2. Prefijo wasapi/ directo
    if f"wasapi/{dev_str}" in valid_names:
        return f"wasapi/{dev_str}"

    # 3. Migración transparente de GUID heredado de VLC ({0.0.0.00000000}.{guid} o {guid})
    import re
    guid_match = re.search(r'\{[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}', dev_str)
    if guid_match:
        guid_only = guid_match.group(0).lower()
        for d_name in valid_names:
            if guid_only in d_name.lower():
                log_playback(f"Dispositivo de audio migrado automáticamente de GUID '{dev_str}' a '{d_name}'")
                return d_name

    # 4. Coincidencia por descripción
    for d in device_list:
        d_desc = d.get('description', '').lower()
        d_name = d.get('name', '')
        if d_desc and dev_str.lower() in d_desc:
            log_playback(f"Dispositivo de audio asociado por descripción '{dev_str}' a '{d_name}'")
            return d_name

    # 5. Fallback seguro a 'auto' si el dispositivo no existe en el sistema actual
    log_playback(f"Dispositivo de audio '{dev_str}' no existe en el sistema. Aplicando fallback seguro a 'auto' para evitar fallo de audio.", level="WARNING")
    return 'auto'


def create_mpv_player(wid=None, hwdec='auto', audio_device=None, ytdl=True):
    """
    Crea y configura una instancia de mpv.MPV:
    - wid: HWND nativo de Windows para embeber el área de vídeo.
    - hwdec: 'auto' para aceleración por hardware.
    - osc=False: desactiva la UI interna de mpv.
    - input_vo_keyboard=False: evita que el HWND de vídeo capture el foco del lector de pantalla.
    """
    mpv_mod = get_mpv_module()
    if not mpv_mod:
        log_playback("get_mpv_module() retornó None. libmpv no está disponible.", level="ERROR")
        return None

    _ensure_c_numeric_locale()

    ytdlp_bin = get_external_ytdlp_exe()
    mpv_log_file = get_mpv_log_path().replace('\\', '/')

    opts = {
        'hwdec': hwdec,
        'osc': False,
        'osd_level': 0,
        'keep_open': 'yes',
        'input_default_bindings': False,
        'input_vo_keyboard': False,
        'log_file': mpv_log_file,
        'msg_level': 'all=v',
    }
    if wid is not None:
        opts['wid'] = wid

    if ytdl and ytdlp_bin and os.path.isfile(ytdlp_bin):
        opts['ytdl'] = True
        normalized_ytdlp = ytdlp_bin.replace('\\', '/')
        opts['script_opts'] = f'ytdl_hook-ytdl_path={normalized_ytdlp}'
    else:
        opts['ytdl'] = False

    def _mpv_log_handler(level, prefix, text):
        t = text.strip() if text else ""
        if t and level in ('error', 'fatal', 'warn'):
            log_playback(f"[MPV:{prefix}] {t}", level=level.upper())

    log_playback(f"Iniciando creación de MPV (wid={wid}, hwdec={hwdec}, audio_device='{audio_device}', ytdl={opts.get('ytdl')}, log_file='{mpv_log_file}')")

    player = None
    try:
        player = mpv_mod.MPV(log_handler=_mpv_log_handler, loglevel='info', **opts)
    except Exception as e1:
        log_playback(f"Fallo al instanciar MPV con wid. Intentando fallback sin wid: {e1}", level="WARNING", exc=e1)
        try:
            opts_fallback = dict(opts)
            opts_fallback.pop('wid', None)
            player = mpv_mod.MPV(log_handler=_mpv_log_handler, loglevel='info', **opts_fallback)
            if wid is not None:
                try:
                    player.wid = wid
                except Exception as e_wid:
                    log_playback(f"No se pudo asignar player.wid posterior: {e_wid}", level="WARNING")
        except Exception as e2:
            log_playback(f"Error crítico al instanciar MPV: {e2}", level="ERROR", exc=e2)
            print(f"Error al crear reproductor MPV: {e2}")
            return None

    if opts.get('ytdl'):
        from config_manager import get_ytdlp_extractor_args
        raw_opts = {}
        ext_arg = get_ytdlp_extractor_args()
        if ext_arg:
            raw_opts['extractor-args'] = ext_arg
        else:
            raw_opts['extractor-args'] = 'youtube:player_client=android,ios,web'
        try:
            player['ytdl-raw-options'] = raw_opts
        except Exception as e_ytdl:
            log_playback(f"Fallo al asignar ytdl-raw-options a MPV: {e_ytdl}", level="WARNING")

    target_dev = resolve_mpv_audio_device(audio_device, player=player)
    try:
        player['audio-device'] = target_dev
        log_playback(f"Dispositivo de audio configurado en MPV: '{target_dev}'")
    except Exception as e_aud:
        log_playback(f"No se pudo aplicar audio-device '{target_dev}' en MPV: {e_aud}. Fallback a 'auto'", level="WARNING")
        try:
            player['audio-device'] = 'auto'
        except Exception:
            pass

    log_playback("Instancia de MPV creada y lista para reproducción.")
    return player


def obtener_dispositivos_audio():
    """
    Retorna una lista de tuplas (device_id, device_name) con los dispositivos de salida de audio disponibles.
    El primer elemento es siempre ('', 'Predeterminado del sistema').
    """
    devices = [('', 'Predeterminado del sistema')]
    seen_ids = set(['', 'auto'])
    _ensure_c_numeric_locale()
    mpv_mod = get_mpv_module()
    if mpv_mod:
        try:
            temp_p = mpv_mod.MPV(hwdec='no', osc=False, ytdl=False)
            raw_list = getattr(temp_p, 'audio_device_list', []) or []
            for d in raw_list:
                name = d.get('name', '')
                desc = d.get('description', '') or name
                if name and name not in seen_ids and not name.lower().startswith('openal'):
                    devices.append((name, desc))
                    seen_ids.add(name)
            temp_p.terminate()
        except Exception:
            pass
    return devices


def probar_dispositivo_audio(dev_id):
    """Reproduce un breve tono de prueba en el dispositivo de salida indicado usando libmpv."""
    _ensure_c_numeric_locale()
    mpv_mod = get_mpv_module()
    if not mpv_mod:
        accessibility.speak("libmpv no está disponible.")
        return

    def _worker():
        try:
            player = mpv_mod.MPV(hwdec='no', osc=False, ytdl=False)
            if dev_id:
                try:
                    player['audio-device'] = dev_id
                except Exception:
                    pass
            # Cargar sonido de prueba si existe, o generar tono sintético lavfi
            base_dir = get_base_dir()
            test_sound = os.path.join(base_dir, 'resources', 'sounds', 'test.wav')
            if os.path.isfile(test_sound):
                player.play(test_sound)
            else:
                player.play("av://lavfi:sine=frequency=440:duration=0.5")
            player.wait_for_playback()
            player.terminate()
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()
    return True


def mostrar_notificacion_bandeja(titulo: str = "YouTube Downloader", mensaje: str = "librería descargada con éxito"):
    """Muestra una notificación en la bandeja del sistema de Windows y la anuncia por voz."""
    accessibility.speak(mensaje)
    try:
        nm = wx.adv.NotificationMessage(title=titulo, message=mensaje)
        nm.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)
    except Exception:
        pass

    if sys.platform == 'win32':
        ps_code = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $ni = New-Object System.Windows.Forms.NotifyIcon
        $ni.Icon = [System.Drawing.SystemIcons]::Information
        $ni.Visible = $true
        $ni.ShowBalloonTip(4000, '{titulo}', '{mensaje}', [System.Windows.Forms.ToolTipIcon]::Info)
        Start-Sleep -Seconds 3
        $ni.Dispose()
        """
        try:
            import subprocess
            subprocess.Popen(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_code],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass


def pedir_confirmacion_eliminar_favorito(parent, titulo="el elemento"):
    """
    Solicita confirmación al usuario para eliminar un elemento de favoritos si la opción
    está activada en la configuración ('confirmar_eliminar_favorito').
    Por defecto se pide confirmación.
    """
    mod_ui = sys.modules.get('ui')
    cargar_fn = getattr(mod_ui, 'cargar_configuracion', cargar_configuracion) if mod_ui else cargar_configuracion
    cfg = cargar_fn()
    if cfg.get('confirmar_eliminar_favorito', True):
        msg = f"¿Estás seguro de que deseas eliminar de favoritos:\n\"{titulo}\"?"
        resp = wx.MessageBox(
            msg,
            "Confirmar eliminación de favorito",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            parent
        )
        return resp == wx.YES
    return True
