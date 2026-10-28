"""
Módulo de actualización automática portable para el Descargador de YouTube.
Consulta buscaapps.com/youtube/version.json, avisa de forma accesible y
aplica la actualización mediante un script de relevo sin perder configuraciones.
"""

import os
import sys
import json
import time
import urllib.request
import tempfile
import subprocess
import threading
import shutil
import uuid
from update_transaction import UPDATE_SCRIPT
import wx
import accessibility

APP_VERSION = "1.6.1"
APP_NAME = "Descargador de YouTube"
CHECK_UPDATE_URL = "https://raw.githubusercontent.com/joseonce/youtube-downloader/main/version.json"
FALLBACK_UPDATE_URL = "https://buscaapps.com/youtube/version.json"


def get_base_dir():
    """Retorna el directorio base de la aplicación (carpeta del ejecutable o script principal)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def parse_version(v_str):
    """
    Convierte cadenas como '1.3.0', 'v1.3.1', '1.4' en una tupla de enteros
    para realizar comparaciones de versión fiables.
    """
    try:
        clean = str(v_str).strip().lstrip('v').strip()
        parts = [int(p) for p in clean.split('.') if p.isdigit()]
        return tuple(parts) if parts else (0, 0, 0)
    except Exception:
        return (0, 0, 0)


def check_for_app_update():
    """
    Consulta version.json en GitHub (servidor principal) o buscaapps.com (servidor de respaldo).
    Retorna el diccionario con la información si hay una versión superior,
    o None si ya está al día o aún no se ha publicado version.json.
    """
    for url in (CHECK_UPDATE_URL, FALLBACK_UPDATE_URL):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"YouTubeDownloader/{APP_VERSION} (Portable; Windows)"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status == 200:
                    content = response.read().decode('utf-8')
                    data = json.loads(content)
                    remote_ver = data.get("version", "0.0.0")
                    if parse_version(remote_ver) > parse_version(APP_VERSION):
                        return data
                    return None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
        except Exception:
            continue
    return None


def launch_portable_updater(zip_path):
    """Preparar el relevo independiente; cerrar solo cuando ya se haya lanzado."""
    base_dir = get_base_dir()
    work = tempfile.mkdtemp(prefix="yt_update_")
    try:
        package = os.path.join(work, "package.zip")
        shutil.move(zip_path, package)

        work_sound = None
        base_sound = os.path.join(base_dir, "resources", "sounds", "espera.wav")
        if not os.path.isfile(base_sound):
            try:
                import sound_manager
                sound_manager.ensure_sound_files()
            except Exception:
                pass
        if os.path.isfile(base_sound):
            try:
                work_sound = os.path.join(work, "espera.wav")
                shutil.copy2(base_sound, work_sound)
            except Exception:
                work_sound = None

        settings = {
            "target": base_dir,
            "work": work,
            "zip": package,
            "sound": work_sound,
            "token": uuid.uuid4().hex,
            "pid": os.getpid(),
            "entry": os.path.basename(sys.executable) if getattr(sys, "frozen", False) else "app.py",
            "python": None if getattr(sys, "frozen", False) else sys.executable,
        }
        settings_path = os.path.join(work, "settings.json")
        script_path = os.path.join(work, "install.ps1")
        with open(settings_path, "w", encoding="utf-8") as stream:
            json.dump(settings, stream, ensure_ascii=False)
        with open(script_path, "w", encoding="utf-8-sig") as stream:
            stream.write(UPDATE_SCRIPT)
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-WindowStyle", "Hidden", "-File", script_path, "-Settings", settings_path],
            cwd=tempfile.gettempdir(),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True,
        )
    except Exception:
        shutil.rmtree(work)
        raise

    # Cerrar la interfaz gráfica y la aplicación de manera limpia e inmediata
    try:
        if hasattr(wx, 'GetApp') and wx.GetApp():
            app = wx.GetApp()
            for win in wx.GetTopLevelWindows():
                try:
                    win.Hide()
                    win.Destroy()
                except Exception:
                    pass
            app.ExitMainLoop()
    except Exception:
        pass

    try:
        accessibility.shutdown_accessibility()
    except Exception:
        pass

    time.sleep(0.5)
    os._exit(0)


class AppUpdateDialog(wx.Dialog):
    """
    Diálogo accesible para informar al usuario de una nueva versión disponible,
    mostrar notas de lanzamiento y descargar la actualización portable.
    """
    def __init__(self, parent, update_info):
        super().__init__(
            parent,
            title="Nueva versión disponible - Descargador de YouTube",
            size=(560, 420),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )

        self.update_info = update_info
        self.v_nueva = update_info.get("version", "Desconocida")
        self.fecha = update_info.get("date", "")
        self.download_url = update_info.get("url", "")
        self.fallback_download_url = update_info.get("fallback_url", "")
        self._is_downloading = False

        sizer = wx.BoxSizer(wx.VERTICAL)

        # 1. Cabecera con versiones
        box_header = wx.StaticBox(self, label="Información de actualización")
        sizer_header = wx.StaticBoxSizer(box_header, wx.VERTICAL)

        info_txt = f"¡Hay una nueva versión disponible del Descargador de YouTube!\n" \
                   f"• Versión disponible: {self.v_nueva}" + (f" ({self.fecha})" if self.fecha else "") + "\n" \
                   f"• Versión instalada actualmente: {APP_VERSION}"
        self.lbl_versiones = wx.StaticText(box_header, label=info_txt)
        self.lbl_versiones.SetFont(self.lbl_versiones.GetFont().Bold())
        sizer_header.Add(self.lbl_versiones, 0, wx.ALL, 8)
        sizer.Add(sizer_header, 0, wx.EXPAND | wx.ALL, 10)

        # 2. Lista de novedades / changelog
        sizer.Add(wx.StaticText(self, label="&Novedades de esta versión:"), 0, wx.LEFT | wx.RIGHT, 10)
        changelog = update_info.get("changelog", [])
        if isinstance(changelog, list):
            changelog_txt = "\n".join(f"• {c}" for c in changelog)
        else:
            changelog_txt = str(changelog)

        self.txt_changelog = wx.TextCtrl(
            self,
            value=changelog_txt,
            style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        sizer.Add(self.txt_changelog, 1, wx.EXPAND | wx.ALL, 10)

        # 3. Barra de progreso y estado
        self.gauge = wx.Gauge(self, range=100, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        sizer.Add(self.gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.lbl_estado = wx.StaticText(
            self,
            label="Pulsa 'Actualizar ahora' para descargar e instalar la actualización."
        )
        sizer.Add(self.lbl_estado, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # 4. Botones de acción
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_update = wx.Button(self, label="&Actualizar ahora")
        self.btn_update.SetDefault()
        self.btn_update.Bind(wx.EVT_BUTTON, self.on_start_download)
        btn_sizer.Add(self.btn_update, 0, wx.RIGHT, 10)

        self.btn_cancel = wx.Button(self, wx.ID_CANCEL, "&Más tarde")
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_sizer.Add(self.btn_cancel, 0)

        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 12)

        self.SetSizer(sizer)
        self.CenterOnParent()

        # Locución accesible para lectores de pantalla
        accessibility.speak(
            f"Nueva versión {self.v_nueva} disponible de Descargador de YouTube. "
            f"Tu versión actual es {APP_VERSION}."
        )

    def on_cancel(self, event):
        if self._is_downloading:
            res = wx.MessageBox(
                "La descarga de la actualización está en curso.\n¿Deseas cancelarla?",
                "Cancelar actualización",
                wx.YES_NO | wx.ICON_QUESTION,
                self
            )
            if res != wx.YES:
                return
        self._is_downloading = False
        self.EndModal(wx.ID_CANCEL)

    def on_start_download(self, event):
        if self._is_downloading:
            return
        if not self.download_url:
            wx.MessageBox("No se especificó la URL de descarga de la actualización.", "Error", wx.OK | wx.ICON_ERROR, self)
            return

        self._is_downloading = True
        self.btn_update.Enable(False)
        self.lbl_estado.SetLabel("Iniciando descarga de la actualización...")
        accessibility.speak("Iniciando descarga de la nueva versión. Por favor, espera...")

        threading.Thread(target=self._download_worker, daemon=True).start()

    def _download_worker(self):
        fd, temp_zip = tempfile.mkstemp(prefix="yt_download_", suffix=".zip")
        os.close(fd)
        urls_to_try = [u for u in [self.download_url, self.fallback_download_url] if u]
        last_error = None

        for download_url in urls_to_try:
            try:
                req = urllib.request.Request(
                    download_url,
                    headers={"User-Agent": f"YouTubeDownloader/{APP_VERSION} (Portable Updater)"}
                )
                with urllib.request.urlopen(req, timeout=30) as resp, open(temp_zip, 'wb') as out_f:
                    total_size = int(resp.headers.get('Content-Length', 0))
                    downloaded = 0
                    block_size = 65536
                    last_reported_pct = -1

                    while True:
                        if not self._is_downloading:
                            out_f.close()
                            try:
                                os.remove(temp_zip)
                            except Exception:
                                pass
                            return

                        chunk = resp.read(block_size)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            pct = int((downloaded / total_size) * 100)
                            if pct != last_reported_pct:
                                last_reported_pct = pct
                                wx.CallAfter(self._update_progress, pct, downloaded, total_size)

                wx.CallAfter(self._on_download_finished, temp_zip)
                return
            except Exception as e:
                last_error = e
                # Si falló la primera URL, limpia el archivo parcial antes de intentar el fallback
                try:
                    with open(temp_zip, 'wb') as out_f:
                        pass
                except Exception:
                    pass

        try:
            os.remove(temp_zip)
        except FileNotFoundError:
            pass
        wx.CallAfter(self._on_download_error, str(last_error) if last_error else "Error de descarga desconocido")

    def _update_progress(self, percent, downloaded, total):
        self.gauge.SetValue(percent)
        mb_down = downloaded / (1024 * 1024)
        mb_total = total / (1024 * 1024)
        self.lbl_estado.SetLabel(f"Descargando: {percent}% ({mb_down:.1f} MB de {mb_total:.1f} MB)...")
        # Locución cada 25% para no saturar el lector de pantalla
        if percent in (25, 50, 75):
            accessibility.speak(f"Descargando actualización: {percent} por ciento.")

    def _on_download_finished(self, temp_zip):
        self.gauge.SetValue(100)
        self.lbl_estado.SetLabel("¡Descarga completada! Preparando la actualización...")
        self.btn_cancel.Enable(False)

        msg = (
            "La nueva versión se ha descargado correctamente.\n\n"
            "La aplicación se cerrará ahora para actualizar los archivos.\n"
            "Al finalizar, la aplicación se abrirá automáticamente.\n"
            "Si falla, se restaurará la versión anterior."
        )
        accessibility.speak(
            "Descarga completada con éxito. La aplicación se cerrará para aplicar la actualización. "
            "La aplicación se abrirá automáticamente cuando termine."
        )
        try:
            self.Raise()
            self.SetFocus()
        except Exception:
            pass
        wx.MessageBox(
            msg,
            "Actualización descargada - Descargador de YouTube",
            wx.OK | wx.ICON_INFORMATION,
            self
        )
        try:
            self.EndModal(wx.ID_OK)
        except Exception:
            pass
        try:
            launch_portable_updater(temp_zip)
        except Exception as exc:
            wx.MessageBox(f"No se pudo iniciar la actualización. La aplicación sigue intacta.\n\n{exc}",
                          "Error de actualización", wx.OK | wx.ICON_ERROR)

    def _on_download_error(self, err_msg):
        self._is_downloading = False
        self.btn_update.Enable(True)
        self.lbl_estado.SetLabel("Error al descargar la actualización.")
        accessibility.speak("Se ha producido un error durante la descarga de la actualización.")
        wx.MessageBox(
            f"No se pudo descargar la nueva versión:\n\n{err_msg}",
            "Error de actualización",
            wx.OK | wx.ICON_ERROR,
            self
        )


def start_background_check(parent_window):
    """
    Inicia una comprobación silenciosa al arrancar la aplicación en segundo plano.
    Si hay una nueva versión disponible, despliega el diálogo accesible.
    """
    def _worker():
        # Esperar 2.5 segundos para que la UI termine de inicializarse y hablar
        time.sleep(2.5)
        try:
            update_info = check_for_app_update()
            if update_info and parent_window:
                wx.CallAfter(lambda: AppUpdateDialog(parent_window, update_info).ShowModal())
        except Exception:
            pass  # En comprobación silenciosa no mostramos errores de conexión

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def manual_check_for_updates(parent_window):
    """
    Comprobación interactiva lanzada por el usuario desde el menú Ayuda.
    Muestra información clara tanto si hay actualización como si ya está al día.
    """
    accessibility.speak("Comprobando actualizaciones de la aplicación...")

    def _worker():
        try:
            update_info = check_for_app_update()
            if update_info:
                wx.CallAfter(lambda: AppUpdateDialog(parent_window, update_info).ShowModal())
            else:
                msg = f"Ya dispones de la versión más reciente del Descargador de YouTube (v{APP_VERSION})."
                def _show_ok():
                    accessibility.speak("Ya tienes instalada la versión más reciente.")
                    wx.MessageBox(msg, "Aplicación al día", wx.OK | wx.ICON_INFORMATION, parent_window)
                wx.CallAfter(_show_ok)
        except Exception as e:
            def _show_err():
                accessibility.speak("No se pudo comprobar las actualizaciones.")
                wx.MessageBox(
                    f"No se pudo conectar con el servidor de actualizaciones:\n\n{e}",
                    "Error de conexión",
                    wx.OK | wx.ICON_WARNING,
                    parent_window
                )
            wx.CallAfter(_show_err)

    threading.Thread(target=_worker, daemon=True).start()
