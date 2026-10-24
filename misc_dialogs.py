"""
Diálogos auxiliares (actualización, atajos de teclado, descripción detallada) y utilidades de navegación.
"""

import os
import sys
import threading
import wx
import wx.adv
import wx.html2

import accessibility
import sound_manager
import updater
from config_manager import get_bin_dir, get_app_data_dir, cargar_configuracion
from streaming import get_current_version, check_nightly_version, download_file_with_progress
from media_utils import formatear_tamano
from ui_vlc import mostrar_notificacion_bandeja


class UpdateDialog(wx.Dialog):
    """Diálogo accesible para comprobar y actualizar yt-dlp a la versión Nightly."""
    def __init__(self, parent, auto_start_download=False):
        super().__init__(parent, title="Actualizar yt-dlp (Versión Nightly)", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        
        self.auto_start_download = auto_start_download
        self.version_actual = get_current_version()
        self.info_nightly = None
        self._cancel = False

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Información de versiones
        box_ver = wx.StaticBox(self, label="Estado de las versiones")
        sizer_ver = wx.StaticBoxSizer(box_ver, wx.VERTICAL)

        self.lbl_ver_actual = wx.StaticText(box_ver, label=f"Versión actual instalada: {self.version_actual}")
        self.lbl_ver_actual.SetFont(self.lbl_ver_actual.GetFont().Bold())
        sizer_ver.Add(self.lbl_ver_actual, 0, wx.ALL, 6)

        self.lbl_ver_nightly = wx.StaticText(box_ver, label="Última versión Nightly: (Pulsa 'Buscar' para consultar)")
        sizer_ver.Add(self.lbl_ver_nightly, 0, wx.ALL, 6)

        sizer.Add(sizer_ver, 0, wx.EXPAND | wx.ALL, 10)

        # Progreso
        self.gauge_update = wx.Gauge(self, range=100, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        sizer.Add(self.gauge_update, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.lbl_estado = wx.StaticText(self, label="Listo para comprobar actualizaciones.")
        sizer.Add(self.lbl_estado, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Botones
        row_btn = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_check = wx.Button(self, label="&Buscar actualizaciones")
        self.btn_check.Bind(wx.EVT_BUTTON, self.on_check_update)
        row_btn.Add(self.btn_check, 0, wx.RIGHT, 8)

        self.btn_update = wx.Button(self, label="&Actualizar a Nightly ahora")
        self.btn_update.Enable(False)
        self.btn_update.Show(False)
        self.btn_update.Bind(wx.EVT_BUTTON, self.on_do_update)
        row_btn.Add(self.btn_update, 0, wx.RIGHT, 8)

        self.btn_close = wx.Button(self, wx.ID_CANCEL, "&Cerrar")
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_close_dialog)
        row_btn.Add(self.btn_close, 0)

        sizer.Add(row_btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        self.SetSizer(sizer)
        self.SetSize((520, 290))
        self.CenterOnParent()
        self.SetEscapeId(self.btn_close.GetId())
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

        # Iniciar comprobación automáticamente al abrir
        wx.CallAfter(self.on_check_update, None)

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.on_close_dialog()
        else:
            event.Skip()

    def on_close_dialog(self, event=None):
        if self.IsModal():
            self.EndModal(wx.ID_CLOSE)
        else:
            self.Close()

    def on_check_update(self, event):
        self.btn_check.Enable(False)
        self.btn_update.Enable(False)
        self.lbl_estado.SetLabel("Consultando última versión Nightly en GitHub...")
        accessibility.speak("Buscando actualización Nightly de yt-dlp...")

        def _worker():
            try:
                info = check_nightly_version()
                wx.CallAfter(self._on_check_success, info)
            except Exception as e:
                wx.CallAfter(self._on_check_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_check_success(self, info):
        self.info_nightly = info
        v_nightly = info['version']
        self.lbl_ver_nightly.SetLabel(f"Última versión Nightly disponible: {v_nightly}")

        if self.auto_start_download:
            self.lbl_estado.SetLabel("Iniciando descarga de la librería necesaria...")
            self.on_do_update(None)
            return

        if v_nightly != self.version_actual:
            self.lbl_estado.SetLabel("¡Hay una versión más reciente disponible! Pulsa 'Actualizar a Nightly ahora'.")
            self.btn_check.Show(False)
            self.btn_update.Show(True)
            self.btn_update.Enable(True)
            self.btn_update.SetDefault()
            self.btn_close.SetLabel("&Cerrar")
            accessibility.speak(f"Nueva versión Nightly encontrada: {v_nightly}. Lista para actualizar.")
        else:
            self.lbl_estado.SetLabel("Ya dispones de la versión Nightly más reciente.")
            self.btn_check.Show(False)
            self.btn_update.Show(False)
            self.btn_update.Enable(False)
            self.btn_close.SetLabel("&Aceptar")
            self.btn_close.SetFocus()
            self.btn_close.SetDefault()
            accessibility.speak("Ya tienes instalada la versión más reciente de yt-dlp.")
        self.Layout()

    def _on_check_error(self, err):
        self.btn_check.Show(True)
        self.btn_check.Enable(True)
        self.lbl_estado.SetLabel("Error al comprobar actualizaciones.")
        self.Layout()
        wx.MessageBox(f"No se pudo comprobar la versión Nightly:\n\n{err}", "Error", wx.OK | wx.ICON_ERROR, self)

    def on_do_update(self, event):
        if not self.info_nightly:
            return

        self.btn_check.Enable(False)
        self.btn_update.Enable(False)
        self.btn_close.Enable(False)
        self.gauge_update.SetValue(0)
        self.lbl_estado.SetLabel("Descargando ejecutable yt-dlp...")
        accessibility.speak("Iniciando descarga y actualización de yt-dlp a la versión Nightly...")

        download_url = self.info_nightly['download_url']
        dest_exe = os.path.join(get_app_data_dir(), 'yt-dlp.exe')

        def _progress(percent, downloaded, total):
            wx.CallAfter(self._on_download_prog, percent, downloaded, total)

        def _worker():
            try:
                download_file_with_progress(download_url, dest_exe, _progress)
                wx.CallAfter(self._on_download_complete)
            except Exception as e:
                wx.CallAfter(self._on_download_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_download_prog(self, percent, downloaded, total):
        self.gauge_update.SetValue(percent)
        desc = formatear_tamano(downloaded)
        tot = formatear_tamano(total)
        self.lbl_estado.SetLabel(f"Descargando actualización: {percent}% ({desc} de {tot})")

    def _on_download_complete(self):
        self.gauge_update.SetValue(100)
        self.version_actual = get_current_version()
        self.lbl_ver_actual.SetLabel(f"Versión actual instalada: {self.version_actual}")
        self.lbl_estado.SetLabel("¡Actualización finalizada con éxito! Ya dispones de la versión Nightly más reciente.")
        self.btn_check.Show(False)
        self.btn_update.Show(False)
        self.btn_update.Enable(False)
        self.btn_close.Enable(True)
        self.btn_close.SetLabel("&Aceptar")
        self.btn_close.SetFocus()
        self.btn_close.SetDefault()
        self.Layout()
        # Notificación en bandeja de sistema y lectura por voz
        mostrar_notificacion_bandeja("YouTube Downloader", "librería descargada con éxito")
        accessibility.speak("Actualización a versión Nightly completada con éxito.")

    def _on_download_error(self, err):
        self.btn_check.Show(True)
        self.btn_check.Enable(True)
        self.btn_update.Show(True)
        self.btn_update.Enable(True)
        self.btn_close.Enable(True)
        self.gauge_update.SetValue(0)
        self.lbl_estado.SetLabel("Error durante la actualización.")
        self.Layout()
        wx.MessageBox(f"Error al descargar la actualización Nightly:\n\n{err}", "Error", wx.OK | wx.ICON_ERROR, self)


class ShortcutsDialog(wx.Dialog):
    """Diálogo accesible con el listado de atajos de teclado."""
    def __init__(self, parent):
        super().__init__(parent, title="Atajos de teclado", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        help_text = (
            "ATAJOS GENERALES DE LA APLICACIÓN:\n"
            "• Ctrl + F  o  Alt + B: Ir al campo de búsqueda\n"
            "• Menú contextual en búsqueda: Acciones para Canales y Listas de reproducción\n"
            "• Enter en búsqueda: Iniciar búsqueda multimedia o explorar canal/playlist\n"
            "• Flechas Arriba / Abajo: Navegar entre los elementos de la lista\n"
            "• Flechas Izquierda / Derecha: Navegar y anunciar columnas de la fila actual\n"
            "• Barra Espaciadora: Marcar / Desmarcar elemento para descarga/reproducción múltiple\n"
            "• Ctrl + A: Seleccionar todos los elementos\n"
            "• Ctrl + P: Reproducir selección (o elemento actual)\n"
            "• Ctrl + L: Reproducir toda la lista de resultados de forma continua\n"
            "• Ctrl + H: Ver y gestionar listas de Favoritos\n"
            "• Ctrl + Shift + H: Cargar Historial de reproducciones de YouTube\n"
            "• Ctrl + Shift + W: Cargar lista \"Ver más tarde\" de YouTube\n"
            "• Ctrl + Shift + Y: Cargar mis listas de reproducción de YouTube\n"
            "• Ctrl + B: Añadir o quitar el vídeo seleccionado de Favoritos (permite elegir o crear lista)\n"
            "• Tecla Supr: Eliminar el elemento seleccionado de Favoritos (con confirmación configurable)\n"
            "• Ctrl + Shift + P: Reproducir vídeos de Favoritos en secuencia continua\n"
            "• Enter en la lista: Abrir playlist o reproducir vídeo\n"
            "• Ctrl + D: Descargar elementos seleccionados\n"
            "• Escape: Retroceder un nivel de navegación (vídeos -> lista -> canal -> favoritos/búsqueda) o limpiar resultados\n"
            "• Alt + Flecha Izquierda: Retroceder al nivel anterior en la lista de resultados\n"
            "• Ctrl + , : Abrir diálogo de Opciones y Preferencias\n"
            "• Ctrl + U: Actualizar yt-dlp a la versión Nightly\n"
            "• Ctrl + C: Copiar enlace del elemento seleccionado al portapapeles\n"
            "• Ctrl + O: Abrir la carpeta de descargas en el explorador de archivos\n"
            "• F1: Mostrar esta ayuda de atajos\n"
            "• Alt + F4: Salir de la aplicación\n\n"
            "CONTROLES DENTRO DEL REPRODUCTOR MULTIMEDIA:\n"
            "• Tecla P: Reproducir / Pausar\n"
            "• Tecla S: Detener reproducción\n"
            "• Tecla A: Activar / Desactivar modo aleatorio (Shuffle)\n"
            "• Espacio: Accionar el botón enfocado en la ventana del reproductor\n"
            "• Flechas Arriba / Abajo: Subir / Bajar volumen (+/- 5%)\n"
            "• Tecla M: Silenciar / Activar sonido (Mute)\n"
            "• Ctrl + Derecha / Tecla N: Avanzar a la siguiente canción de la lista en reproducción\n"
            "• Ctrl + Izquierda: Retroceder a la canción anterior de la lista en reproducción\n"
            "• Tecla F  o  Tecla B: Añadir o quitar de Favoritos\n"
            "• Tecla Supr: Eliminar el elemento en reproducción de Favoritos (con confirmación configurable)\n"
            "• Tecla R: Activar / Desactivar repetición continua (bucle)\n"
            "• F6: Disminuir velocidad de reproducción (-0,1x hasta un mínimo de 0,5x)\n"
            "• F7: Aumentar velocidad de reproducción (+0,1x hasta un máximo de 2,0x)\n"
            "• F8: Anunciar porcentaje de reproducción al lector de pantalla\n"
            "• F11: Activar o desactivar ventana de vídeo (alternar modo solo audio)\n"
            "• F9: Anunciar tiempo transcurrido al lector de pantalla\n"
            "• F10: Anunciar tiempo restante al lector de pantalla\n"
            "• Ctrl + Shift + C  o  Ctrl + C: Copiar enlace del vídeo en reproducción al portapapeles\n"
            "• Ctrl + D: Descargar la pista en reproducción\n"
            "• Escape: Cerrar reproductor y volver a la lista\n"
            "• Flechas Izquierda / Derecha: Retroceder / Avanzar 10 segundos en la pista\n"
            "• Shift + Flechas: Retroceder / Avanzar 1 segundo\n"
            "• Shift + Alt + Flechas: Retroceder / Avanzar 5 segundos\n"
            "• Ctrl + Shift + Flechas: Retroceder / Avanzar 1 minuto\n"
            "• Ctrl + Alt + Shift + Flechas: Retroceder / Avanzar 5 minutos\n"
            "  (Nota: Ctrl + Flechas cambian de canción; Flechas solas o con Shift/Alt buscan dentro de la canción)\n"
        )
        
        text_ctrl = wx.TextCtrl(self, value=help_text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_NONE)
        text_ctrl.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(text_ctrl, 1, wx.EXPAND | wx.ALL, 15)
        
        btn_close = wx.Button(self, wx.ID_OK, "&Cerrar")
        btn_close.SetDefault()
        sizer.Add(btn_close, 0, wx.ALIGN_CENTER | wx.BOTTOM, 15)
        
        self.SetSizer(sizer)
        self.SetSize((580, 520))
        self.CenterOnParent()
        self.SetEscapeId(btn_close.GetId())
        self.Bind(wx.EVT_CHAR_HOOK, lambda e: self.EndModal(wx.ID_OK) if e.GetKeyCode() == wx.WXK_ESCAPE else e.Skip())


class DescriptionDialog(wx.Dialog):
    """
    Diálogo accesible para visualizar la descripción detallada de un vídeo, lista de reproducción o canal,
    con botones para copiar el texto al portapapeles y aceptar/cerrar.
    """
    def __init__(self, parent, video_data, downloader=None):
        self.video = video_data or {}
        self.downloader = downloader
        self._is_closing = False

        tipo_item = self.video.get('tipo_item', '')
        if not tipo_item:
            if self.video.get('is_channel'):
                tipo_item = 'channel'
            elif self.video.get('is_playlist'):
                tipo_item = 'playlist'
            else:
                tipo_item = 'video'

        if tipo_item == 'channel':
            tipo_label = "del canal"
        elif tipo_item == 'playlist':
            tipo_label = "de la lista"
        else:
            tipo_label = "del vídeo"

        raw_title = self.video.get('title') or self.video.get('channel') or "Elemento"
        title_display = (raw_title[:60] + "...") if len(raw_title) > 60 else raw_title

        super().__init__(
            parent,
            title=f"Descripción {tipo_label}: {title_display}",
            size=(700, 520),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX
        )

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Encabezado accesible
        lbl_header = wx.StaticText(self, label=f"Descripción {tipo_label}: {raw_title}")
        lbl_header.SetFont(lbl_header.GetFont().Bold())
        sizer.Add(lbl_header, 0, wx.ALL | wx.EXPAND, 12)

        # Cuadro de texto multilínea de solo lectura
        self.txt_desc = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SUNKEN
        )
        self.txt_desc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.txt_desc, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        # Mensaje de estado accesible
        self.lbl_status = wx.StaticText(self, label="")
        sizer.Add(self.lbl_status, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        # Fila de botones: Copiar y Aceptar
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btn_copiar = wx.Button(self, wx.ID_ANY, "&Copiar al portapapeles")
        self.btn_copiar.Bind(wx.EVT_BUTTON, self.on_copiar)
        btn_sizer.Add(self.btn_copiar, 0, wx.RIGHT, 10)

        self.btn_aceptar = wx.Button(self, wx.ID_OK, "&Aceptar")
        self.btn_aceptar.SetDefault()
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self.on_close)
        btn_sizer.Add(self.btn_aceptar, 0)

        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 12)

        self.SetSizer(sizer)
        self.SetSize((700, 520))
        self.CenterOnParent()
        self.SetEscapeId(self.btn_aceptar.GetId())

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

        # Comprobar si ya existe descripción en caché
        cached_desc = self.video.get('full_description')
        if cached_desc is not None:
            self._mostrar_texto(cached_desc)
        else:
            self.txt_desc.SetValue("Obteniendo descripción, por favor espere...")
            self.btn_copiar.Enable(False)
            cfg = getattr(parent, 'config', {}) if parent else {}
            if not cfg:
                try:
                    cfg = cargar_configuracion()
                except Exception:
                    cfg = {}
            if cfg.get('sonido_espera_descarga', True):
                sound_manager.start_waiting_sound(interval=2.0)
            thread = threading.Thread(target=self._cargar_descripcion_worker, daemon=True)
            thread.start()

    def _cargar_descripcion_worker(self):
        try:
            url = self.video.get('url')
            if not url:
                if self.video.get('id'):
                    if self.video.get('is_playlist'):
                        url = f"https://www.youtube.com/playlist?list={self.video['id']}"
                    elif self.video.get('is_channel'):
                        url = f"https://www.youtube.com/channel/{self.video['id']}"
                    else:
                        url = f"https://www.youtube.com/watch?v={self.video['id']}"

            desc = ""
            if url and self.downloader:
                try:
                    desc = self.downloader.obtener_descripcion(url)
                except Exception:
                    desc = ""

            # Si no se pudo obtener descripción completa pero había un extracto inicial disponible
            if not desc and self.video.get('description'):
                desc = self.video.get('description')

            if not self._is_closing:
                wx.CallAfter(self._on_desc_cargada, desc)
        finally:
            sound_manager.stop_waiting_sound()

    def _on_desc_cargada(self, desc):
        if self._is_closing:
            return
        desc = (desc or "").strip()
        self.video['full_description'] = desc
        self._mostrar_texto(desc)
        if desc:
            accessibility.speak("Descripción cargada.")
        else:
            accessibility.speak("No hay descripción disponible.")

    def _mostrar_texto(self, desc):
        if desc:
            self.txt_desc.SetValue(desc)
            self.btn_copiar.Enable(True)
        else:
            self.txt_desc.SetValue("No hay descripción disponible para este elemento.")
            self.btn_copiar.Enable(False)
        self.txt_desc.SetInsertionPoint(0)

    def on_copiar(self, event):
        texto = self.txt_desc.GetValue()
        if not texto or texto.startswith("Obteniendo descripción") or texto.startswith("No hay descripción disponible"):
            return
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(texto))
            wx.TheClipboard.Close()
            msg = "Descripción copiada al portapapeles."
            self.lbl_status.SetLabel(msg)
            accessibility.speak(msg)
        else:
            msg = "No se pudo acceder al portapapeles."
            self.lbl_status.SetLabel(msg)
            accessibility.speak(msg)

    def on_close(self, event=None):
        sound_manager.stop_waiting_sound()
        self._is_closing = True
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Destroy()

    def on_char_hook(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.on_close(None)
        elif keycode == ord('C') and event.ControlDown() and not isinstance(self.FindFocus(), wx.TextCtrl):
            self.on_copiar(None)
        else:
            event.Skip()


def _navegar_columna(list_ctrl, col_attr_name, owner, delta, status_bar=None):
    """Navega entre columnas de un ListCtrl y anuncia al lector de pantalla."""
    num_items = list_ctrl.GetItemCount()
    if num_items == 0:
        return
    idx = list_ctrl.GetFirstSelected()
    if idx == -1:
        idx = 0
        list_ctrl.Select(0)
        list_ctrl.Focus(0)
    num_cols = list_ctrl.GetColumnCount()
    if num_cols == 0:
        return
    col_actual = getattr(owner, col_attr_name, 0)
    nueva_col = col_actual + delta
    if nueva_col < 0:
        nueva_col = 0
        msg_borde = "Primera columna: "
    elif nueva_col >= num_cols:
        nueva_col = num_cols - 1
        msg_borde = "Última columna: "
    else:
        msg_borde = ""
    setattr(owner, col_attr_name, nueva_col)
    col_header = list_ctrl.GetColumn(nueva_col)
    col_name = col_header.GetText() if col_header else f"Columna {nueva_col + 1}"
    item = list_ctrl.GetItem(idx, nueva_col)
    col_text = item.GetText().strip() if item else ""
    if not col_text and nueva_col == 0:
        col_text = list_ctrl.GetItemText(idx)
    if not col_text:
        col_text = "Sin información"
    anuncio = f"{msg_borde}{col_name}: {col_text}"
    accessibility.speak(anuncio)
    if status_bar:
        status_bar.SetStatusText(anuncio, 0)

