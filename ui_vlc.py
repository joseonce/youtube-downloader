"""
Módulo de integración con libvlc, dispositivos de audio del sistema y notificaciones.
"""

import os
import sys
import threading
import wx
import wx.adv

import accessibility
import sound_manager
from config_manager import get_base_dir, cargar_configuracion

_vlc_initialized = False
vlc = None

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


# Configuración e inicialización de la librería nativa libvlc.dll (en resources/vlc o externa)
_vlc_initialized = False
vlc = None


def init_vlc_env():
    global _vlc_initialized
    if _vlc_initialized:
        return
    base_dir = get_base_dir()
    meipass = getattr(sys, '_MEIPASS', None)

    vlc_candidates = []
    if meipass:
        vlc_candidates.extend([
            os.path.join(meipass, 'resources', 'vlc'),
            os.path.join(meipass, 'resources'),
            meipass
        ])
    vlc_candidates.extend([
        os.path.join(base_dir, 'resources', 'vlc'),
        os.path.join(base_dir, 'resources'),
        os.path.join(base_dir, 'vlc'),
        os.path.join(base_dir, 'YouTubeDownloader', 'resources', 'vlc'),
        os.path.join(base_dir, 'YouTubeDownloader', 'resources'),
        os.path.join(os.path.dirname(base_dir), 'resources', 'vlc'),
        os.path.join(os.path.dirname(base_dir), 'YouTubeDownloader', 'resources', 'vlc'),
        r"C:\portables\YouTubeDownloader\resources\vlc",
        r"C:\portable\YouTubeDownloader\resources\vlc",
        r"C:\portable\resources\vlc",
        r"D:\youtube1\dist\YouTubeDownloader_Portable\resources\vlc",
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC"
    ])

    for vlc_path in vlc_candidates:
        dll_path = os.path.join(vlc_path, 'libvlc.dll') if not vlc_path.endswith('.dll') else vlc_path
        if os.path.isfile(dll_path):
            dir_path = os.path.dirname(dll_path)
            plugins_path = os.path.join(dir_path, 'plugins')
            os.environ['PYTHON_VLC_LIB_PATH'] = dll_path
            if os.path.isdir(plugins_path):
                os.environ['PYTHON_VLC_MODULE_PATH'] = plugins_path
            try:
                os.add_dll_directory(dir_path)
            except Exception:
                pass
            break
    _vlc_initialized = True


def get_vlc_module():
    """Retorna el módulo vlc importado correctamente o None si no está disponible."""
    global vlc
    if vlc is not None:
        return vlc
    init_vlc_env()
    try:
        import vlc as _vlc
        vlc = _vlc
    except Exception:
        vlc = None
    return vlc

init_vlc_env()
vlc = get_vlc_module()




def obtener_dispositivos_audio():
    """
    Retorna una lista de tuplas (device_id, device_name) con los dispositivos de salida de audio disponibles.
    El primer elemento es siempre ('', 'Predeterminado del sistema').
    """
    devices = [('', 'Predeterminado del sistema')]
    seen_ids = set([''])
    _vlc = get_vlc_module()
    if _vlc:
        try:
            inst = _vlc.Instance('--quiet')
            p = inst.media_player_new()
            dev_enum = p.audio_output_device_enum()
            curr = dev_enum
            while curr:
                d = curr.contents
                d_id = d.device.decode('utf-8', errors='ignore') if d.device else ""
                d_desc = d.description.decode('utf-8', errors='ignore') if d.description else ""
                if d_id and d_id not in seen_ids:
                    seen_ids.add(d_id)
                    devices.append((d_id, d_desc or d_id))
                elif not d_id and d_desc and d_desc.lower() not in ('default', 'predeterminado') and d_desc not in seen_ids:
                    seen_ids.add(d_desc)
                    devices.append(('', d_desc))
                curr = d.next
            if hasattr(_vlc, 'libvlc_audio_output_device_list_release') and dev_enum:
                try:
                    _vlc.libvlc_audio_output_device_list_release(dev_enum)
                except Exception:
                    pass
            p.release()
            inst.release()
        except Exception:
            pass
    return devices



def probar_dispositivo_audio(dev_id=''):
    """Reproduce un breve sonido de confirmación en el dispositivo de salida indicado."""
    _vlc = get_vlc_module()
    if not _vlc:
        try:
            import winsound
            if winsound:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass
        return True
    try:
        inst = _vlc.Instance('--quiet')
        player = inst.media_player_new()
        if dev_id:
            try:
                player.audio_output_device_set(None, dev_id)
            except Exception:
                pass
        sound_path = sound_manager.get_sound_file_path('espera.wav')
        sound_manager.ensure_sound_files()
        media = inst.media_new(sound_path)
        player.set_media(media)
        player.audio_set_volume(90)
        player.play()

        def _cleanup():
            import time
            time.sleep(1.0)
            try:
                player.stop()
                player.release()
                inst.release()
            except Exception:
                pass

        threading.Thread(target=_cleanup, daemon=True).start()
        return True
    except Exception:
        return False



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


