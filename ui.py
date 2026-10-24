"""
Interfaz gráfica accesible para el Buscador y Descargador de YouTube con wxPython.
Diseñada para máxima accesibilidad con lectores de pantalla (NVDA, JAWS, Narrador de Windows)
y una arquitectura modular y eficiente.
"""

import os
import re
import sys
import threading
import webbrowser
import wx
import wx.adv
import wx.html2

import accessibility
import sound_manager
import updater

# Re-exportar componentes para compatibilidad transparente
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
    probar_conexion_sesion,
    ENGINES_MAP
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

from downloader import YouTubeDownloader

from ui_vlc import (
    mostrar_notificacion_bandeja,
    init_vlc_env,
    get_vlc_module,
    obtener_dispositivos_audio,
    probar_dispositivo_audio,
    pedir_confirmacion_eliminar_favorito
)

from player_controls_mixin import PlayerControlsMixin
from player_dialog import ProgressBarSlider, VideoCanvasPanel, VideoPreviewDialog
from queue_dialog import ColaReproduccionDialog
from favorites_dialogs import SelectFavoriteListDialog, ChangeFavoriteListDialog, ViewFavoritesChoiceDialog
from options_dialog import OptionsDialog
from misc_dialogs import UpdateDialog, ShortcutsDialog, DescriptionDialog, _navegar_columna

from main_search_mixin import MainSearchMixin
from main_favorites_mixin import MainFavoritesMixin
from main_playback_mixin import MainPlaybackMixin
from main_download_mixin import MainDownloadMixin
from main_list_events_mixin import MainListEventsMixin
from main_lifecycle_mixin import MainLifecycleMixin


class MainFrame(
    MainSearchMixin,
    MainFavoritesMixin,
    MainPlaybackMixin,
    MainDownloadMixin,
    MainListEventsMixin,
    MainLifecycleMixin,
    wx.Frame
):
    def __init__(self):
        super().__init__(
            parent=None,
            title="Descargador de YouTube",
            size=(920, 720),
            style=wx.DEFAULT_FRAME_STYLE
        )

        # Asegurar idioma castellano (español) en wxWidgets
        app = wx.GetApp()
        if app and not getattr(app, '_locale_initialized', False):
            try:
                possible_dirs = []
                if getattr(sys, 'frozen', False):
                    if hasattr(sys, '_MEIPASS'):
                        possible_dirs.append(os.path.join(sys._MEIPASS, 'wx', 'locale'))
                        possible_dirs.append(os.path.join(sys._MEIPASS, 'locale'))
                    exe_dir = os.path.dirname(sys.executable)
                    possible_dirs.append(os.path.join(exe_dir, 'wx', 'locale'))
                    possible_dirs.append(os.path.join(exe_dir, 'locale'))
                else:
                    try:
                        possible_dirs.append(os.path.join(os.path.dirname(wx.__file__), 'locale'))
                    except Exception:
                        pass
                for d in possible_dirs:
                    if os.path.exists(d):
                        wx.Locale.AddCatalogLookupPathPrefix(d)
                app.locale = wx.Locale(wx.LANGUAGE_SPANISH)
                if not app.locale.IsOk():
                    app.locale = wx.Locale(wx.LANGUAGE_SPANISH_MODERN)
                if not app.locale.IsOk():
                    app.locale = wx.Locale(wx.LANGUAGE_DEFAULT)
                app.locale.AddCatalog('wxstd')
            except Exception:
                app.locale = None
            app._locale_initialized = True

        self.downloader = YouTubeDownloader()
        self.config = cargar_configuracion()
        self.downloader.config = self.config
        sound_manager.set_audio_device(self.config.get('audio_output_device', ''))
        accessibility.set_modo_locuciones(self.config.get('modo_locuciones', 'auto'))
        user_home = os.path.expanduser('~')
        default_downloads = os.path.join(user_home, "Downloads") if os.path.exists(os.path.join(user_home, "Downloads")) else user_home
        cfg_destino = (self.config.get('destino_dir') or '').strip()
        self.destino_dir = cfg_destino if cfg_destino else default_downloads
        self.last_selected_row = -1
        self.engine_idx = 0
        self.current_engine = ENGINES_MAP[0][0]
        
        self.resultados = []
        self.cola_descargas = []
        self.cola_reproduccion = []
        self.total_cola = 0
        self.indice_cola = 0
        self.descargas_completadas = 0
        self.descargas_fallidas = 0
        self.last_announced_percent = -1
        self.current_download_percent = 0
        self.current_download_status = None
        self.col_activa_resultados = 0

        # Estado para paginación continua de resultados
        self.last_search_query = ""
        self.last_search_type = 'video'
        self.last_search_engine = ENGINES_MAP[0][0]
        self.last_search_kind = 'search'
        self.last_target_url = ""
        self.next_start_index = 1
        self.is_searching = False
        self.is_showing_favorites = False
        self.modo_boton_buscar = 'buscar'
        self.navigation_stack = []
        self._pending_nav_state = None
        self.current_playlist_title = ""
        self.current_channel_title = ""

        self._init_menu()
        self._init_shortcuts()
        self._init_ui()

        # Barra de estado
        self.status_bar = self.CreateStatusBar(2)
        self.status_bar.SetStatusWidths([-3, -1])
        self.set_status("Listo. Escribe un término de búsqueda o pega una URL de vídeo, canal o playlist.")
        self.actualizar_estados_interfaz()

        self.active_preview_dialog = None
        self._is_shutting_down = False
        self.Bind(wx.EVT_CLOSE, self.on_close_window)
        self.Bind(wx.EVT_ACTIVATE, self.on_frame_activate)

        self.Center()
        self.txt_busqueda.SetFocus()
        accessibility.speak("Descargador de YouTube listo.")

        # Comprobar actualizaciones de la aplicación en segundo plano sin interrumpir al usuario
        updater.start_background_check(self)
        wx.CallAfter(self.verificar_libreria_ytdlp)

    def _init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # ---------------- 1. SECCIÓN DE BÚSQUEDA ----------------
        box_search = wx.StaticBox(panel, label="1. Búsqueda")
        sizer_search = wx.StaticBoxSizer(box_search, wx.HORIZONTAL)

        lbl_search = wx.StaticText(box_search, label="&Términos o URL:")
        sizer_search.Add(lbl_search, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)

        self.txt_busqueda = wx.TextCtrl(box_search, style=wx.TE_PROCESS_ENTER)
        self.txt_busqueda.SetHint("Escribe palabras clave o pega un enlace de vídeo, canal o playlist...")
        self.txt_busqueda.Bind(wx.EVT_TEXT_ENTER, self.on_busqueda_enter)
        self.txt_busqueda.Bind(wx.EVT_CONTEXT_MENU, self.on_busqueda_context_menu)
        self.txt_busqueda.Bind(wx.EVT_SET_FOCUS, self.on_busqueda_set_focus)
        sizer_search.Add(self.txt_busqueda, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)

        lbl_tipo = wx.StaticText(box_search, label="T&ipo:")
        sizer_search.Add(lbl_tipo, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP | wx.BOTTOM, 6)

        tipos_busqueda = ["Vídeos", "Canales", "Listas de reproducción"]
        self.choice_tipo_busqueda = wx.Choice(box_search, choices=tipos_busqueda)
        self.choice_tipo_busqueda.SetSelection(0)
        self.choice_tipo_busqueda.Bind(wx.EVT_CHOICE, self.on_tipo_busqueda_changed)
        self.choice_tipo_busqueda.Enable(self.current_engine == 'ytsearch')
        sizer_search.Add(self.choice_tipo_busqueda, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)
        self.btn_buscar = wx.Button(box_search, label="&Buscar")
        self.btn_buscar.SetToolTip("Busca vídeos, canales o listas de reproducción según los términos introducidos (Alt+B)")
        self.btn_buscar.SetDefault()
        self.btn_buscar.Bind(wx.EVT_BUTTON, self.on_btn_buscar)
        sizer_search.Add(self.btn_buscar, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)

        self.btn_siguientes = wx.Button(box_search, label="&Siguientes resultados")
        self.btn_siguientes.SetToolTip("Carga los siguientes resultados para la búsqueda actual (Alt+S o Ctrl+Shift+N)")
        self.btn_siguientes.Enable(False)
        self.btn_siguientes.Bind(wx.EVT_BUTTON, self.on_btn_siguientes)
        sizer_search.Add(self.btn_siguientes, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)

        main_sizer.Add(sizer_search, 0, wx.EXPAND | wx.ALL, 8)

        # ---------------- 2. SECCIÓN DE RESULTADOS ----------------
        box_results = wx.StaticBox(panel, label="2. Resultados encontrados")
        sizer_results = wx.StaticBoxSizer(box_results, wx.VERTICAL)

        self.lbl_results_info = wx.StaticText(box_results, label="&Lista de resultados (Usa Espacio para marcar vídeos):")
        sizer_results.Add(self.lbl_results_info, 0, wx.LEFT | wx.TOP, 4)

        # Lista en modo reporte limpia y completamente accesible para lectores de pantalla
        self.lista_resultados = wx.ListCtrl(
            box_results,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_VRULES
        )
        self.lista_resultados.InsertColumn(0, "Título", width=440)
        self.lista_resultados.InsertColumn(1, "Canal", width=220)
        self.lista_resultados.InsertColumn(2, "Duración", width=120)
        self.lista_resultados.InsertColumn(3, "Visitas", width=140)

        self._init_item_icons()

        self.lista_resultados.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.lista_resultados.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.on_item_focused)
        self.lista_resultados.Bind(wx.EVT_LEFT_DCLICK, self.on_left_dclick)
        self.lista_resultados.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_left_dclick)
        self.lista_resultados.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.lista_resultados.Bind(wx.EVT_KEY_DOWN, self.on_lista_key_down)

        sizer_results.Add(self.lista_resultados, 1, wx.EXPAND | wx.ALL, 4)
        main_sizer.Add(sizer_results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # ---------------- 3. ACCIONES, PROGRESO Y REPRODUCCIÓN ----------------
        box_actions = wx.StaticBox(panel, label="3. Descarga, Reproducción y Progreso")
        sizer_actions = wx.StaticBoxSizer(box_actions, wx.VERTICAL)

        row_ctrls = wx.BoxSizer(wx.HORIZONTAL)
        lbl_fmt = wx.StaticText(box_actions, label="&Formato:")
        row_ctrls.Add(lbl_fmt, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        formatos_opciones = [
            "Vídeo (Mejor calidad MP4)",
            "Audio MP3 (192 kbps - Estándar)",
            "Audio MP3 (320 kbps - Alta fidelidad)",
            "Audio M4A (Original AAC)",
            "Audio FLAC (Sin pérdida)",
            "Audio WAV (PCM sin comprimir)"
        ]
        self.choice_formato = wx.Choice(box_actions, choices=formatos_opciones)
        saved_fmt = min(self.config.get('formato_idx', 0), len(formatos_opciones) - 1)
        self.choice_formato.SetSelection(saved_fmt)
        self.choice_formato.Bind(wx.EVT_CHOICE, self.on_formato_changed)
        row_ctrls.Add(self.choice_formato, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.btn_descargar = wx.Button(box_actions, label="&Descargar Seleccionado")
        self.btn_descargar.SetFont(self.btn_descargar.GetFont().Bold())
        self.btn_descargar.Bind(wx.EVT_BUTTON, self.on_btn_descargar)
        row_ctrls.Add(self.btn_descargar, 0, wx.RIGHT, 6)

        self.btn_previsualizar = wx.Button(box_actions, label="&Reproducir selección")
        self.btn_previsualizar.Bind(wx.EVT_BUTTON, self.on_previsualizar_video)
        row_ctrls.Add(self.btn_previsualizar, 0, wx.RIGHT, 6)

        self.btn_reproducir_todo = wx.Button(box_actions, label="&Reproducir toda la lista")
        self.btn_reproducir_todo.Bind(wx.EVT_BUTTON, self.reproducir_toda_la_lista)
        row_ctrls.Add(self.btn_reproducir_todo, 0, wx.RIGHT, 6)

        self.btn_add_cola = wx.Button(box_actions, label="A&ñadir a la cola")
        self.btn_add_cola.SetToolTip("Añade los vídeos seleccionados a la cola de reproducción secuencial (Ctrl+Q)")
        self.btn_add_cola.Bind(wx.EVT_BUTTON, self.agregar_a_cola_reproduccion)
        row_ctrls.Add(self.btn_add_cola, 0, wx.RIGHT, 6)

        self.row_ctrls = row_ctrls
        self.btn_reproducir_cola = wx.Button(box_actions, label="Reproducir col&a")
        self.btn_reproducir_cola.SetToolTip("Inicia la reproducción secuencial de la cola acumulada (Ctrl+Shift+Q)")
        self.btn_reproducir_cola.Bind(wx.EVT_BUTTON, self.reproducir_cola)
        self.btn_reproducir_cola.Show(False)
        row_ctrls.Add(self.btn_reproducir_cola, 0, wx.RIGHT, 6)

        self.btn_ver_cola = wx.Button(box_actions, label="&Ver cola...")
        self.btn_ver_cola.SetToolTip("Consulta y gestiona las pistas de la cola de reproducción (Ctrl+J)")
        self.btn_ver_cola.Bind(wx.EVT_BUTTON, self.mostrar_dialogo_cola)
        self.btn_ver_cola.Show(False)
        row_ctrls.Add(self.btn_ver_cola, 0, wx.RIGHT, 6)

        self.btn_cancelar = wx.Button(box_actions, label="&Cancelar descarga")
        self.btn_cancelar.Enable(False)
        self.btn_cancelar.Bind(wx.EVT_BUTTON, self.on_btn_cancelar)
        row_ctrls.Add(self.btn_cancelar, 0, wx.RIGHT, 6)

        self.btn_abrir_carpeta = wx.Button(box_actions, label="&Abrir carpeta")
        self.btn_abrir_carpeta.Bind(wx.EVT_BUTTON, self.on_abrir_carpeta)
        row_ctrls.Add(self.btn_abrir_carpeta, 0)

        sizer_actions.Add(row_ctrls, 0, wx.EXPAND | wx.ALL, 6)

        # Barra de progreso y texto de detalle
        self.gauge_progreso = wx.Gauge(box_actions, range=100, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        sizer_actions.Add(self.gauge_progreso, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        self.lbl_progreso_detalle = wx.StaticText(box_actions, label="Listo para buscar y descargar vídeos.")
        sizer_actions.Add(self.lbl_progreso_detalle, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        main_sizer.Add(sizer_actions, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        panel.SetSizer(main_sizer)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def _init_item_icons(self):
        """Crea la lista de imágenes para iconos visuales accesibles (Vídeo, Canal, Playlist)."""
        self.image_list = wx.ImageList(16, 16, True)

        # 1. Icono de Vídeo: Rectángulo carmesí estilo YouTube con triángulo blanco de play
        bmp_vid = wx.Bitmap(16, 16, 32)
        bmp_vid.UseAlpha()
        dc = wx.MemoryDC(bmp_vid)
        dc.SetBackground(wx.Brush(wx.Colour(0, 0, 0, 0)))
        dc.Clear()
        dc.SetBrush(wx.Brush(wx.Colour(220, 20, 60)))
        dc.SetPen(wx.Pen(wx.Colour(180, 0, 0)))
        dc.DrawRoundedRectangle(0, 1, 16, 14, 3)
        dc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
        dc.SetPen(wx.Pen(wx.Colour(255, 255, 255)))
        dc.DrawPolygon([wx.Point(6, 4), wx.Point(6, 11), wx.Point(12, 8)])
        dc.SelectObject(wx.NullBitmap)
        self.IMG_IDX_VIDEO = self.image_list.Add(bmp_vid)

        # 2. Icono de Canal: Rectángulo azul con silueta de creador/usuario
        bmp_canal = wx.Bitmap(16, 16, 32)
        bmp_canal.UseAlpha()
        dc = wx.MemoryDC(bmp_canal)
        dc.SetBackground(wx.Brush(wx.Colour(0, 0, 0, 0)))
        dc.Clear()
        dc.SetBrush(wx.Brush(wx.Colour(30, 144, 255)))
        dc.SetPen(wx.Pen(wx.Colour(0, 100, 200)))
        dc.DrawRoundedRectangle(0, 1, 16, 14, 3)
        dc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
        dc.SetPen(wx.Pen(wx.Colour(255, 255, 255)))
        dc.DrawCircle(8, 5, 2)
        dc.DrawEllipticArc(4, 9, 8, 8, 0, 180)
        dc.SelectObject(wx.NullBitmap)
        self.IMG_IDX_CHANNEL = self.image_list.Add(bmp_canal)

        # 3. Icono de Lista de reproducción: Rectángulo púrpura con líneas de pistas
        bmp_pl = wx.Bitmap(16, 16, 32)
        bmp_pl.UseAlpha()
        dc = wx.MemoryDC(bmp_pl)
        dc.SetBackground(wx.Brush(wx.Colour(0, 0, 0, 0)))
        dc.Clear()
        dc.SetBrush(wx.Brush(wx.Colour(147, 51, 234)))
        dc.SetPen(wx.Pen(wx.Colour(110, 30, 180)))
        dc.DrawRoundedRectangle(0, 1, 16, 14, 3)
        dc.SetPen(wx.Pen(wx.Colour(255, 255, 255), 2))
        dc.DrawLine(3, 4, 13, 4)
        dc.DrawLine(3, 8, 13, 8)
        dc.DrawLine(3, 12, 10, 12)
        dc.SelectObject(wx.NullBitmap)
        self.IMG_IDX_PLAYLIST = self.image_list.Add(bmp_pl)

        self.lista_resultados.AssignImageList(self.image_list, wx.IMAGE_LIST_SMALL)

    def _get_item_type_and_image(self, item: dict):
        """Retorna (tipo_str, tag_accesible, image_idx) para un elemento."""
        if item.get('is_fav_list') or item.get('tipo_item') == 'fav_list':
            return 'fav_list', '[Lista]', getattr(self, 'IMG_IDX_PLAYLIST', 0)
        tipo = detectar_tipo_elemento(item)
        if tipo == 'channel':
            return 'channel', '[Canal]', getattr(self, 'IMG_IDX_CHANNEL', 0)
        elif tipo == 'playlist':
            return 'playlist', '[Lista]', getattr(self, 'IMG_IDX_PLAYLIST', 0)
        else:
            return 'video', '[Vídeo]', getattr(self, 'IMG_IDX_VIDEO', 0)

    def _get_item_display_title_and_image(self, item: dict, is_fav_view: bool = False):
        """
        Calcula el texto para la columna 0 y el índice del icono de imagen.
        - En favoritos: incluye la etiqueta accesible '[Vídeo] ', '[Canal] ' o '[Lista] ' para que los lectores de pantalla
          y personas videntes identifiquen inmediatamente el tipo de contenido guardado.
        - Si está marcado: añade 'Marcado - '.
        """
        tipo, tag, img_idx = self._get_item_type_and_image(item)
        raw_title = item.get('title', 'Sin título')

        # Limpiar prefijos redundantes para evitar acumulaciones
        title_clean = raw_title
        for p in ('Marcado - ', '[Vídeo] ', '[Canal] ', '[Lista] '):
            if title_clean.startswith(p):
                title_clean = title_clean[len(p):]

        is_sel = item.get('selected', False)
        prefix_sel = "Marcado - " if is_sel else ""

        if is_fav_view:
            display_title = f"{prefix_sel}{tag} {title_clean}"
        else:
            display_title = f"{prefix_sel}{title_clean}"

        return display_title, img_idx

    def set_status(self, text: str, field: int = 0, announce: bool = False):
        if hasattr(self, 'status_bar') and self.status_bar:
            self.status_bar.SetStatusText(text, field)
        if announce:
            accessibility.speak(text)

    def on_formato_changed(self, event):
        idx = self.choice_formato.GetSelection()
        self.config['formato_idx'] = idx
        guardar_configuracion(self.config)
        nombre = self.choice_formato.GetString(idx)
        self.set_status(f"Formato seleccionado: {nombre}", field=0, announce=True)

    def on_busqueda_set_focus(self, event):
        event.Skip()
        wx.CallAfter(self._seleccionar_todo_busqueda)

    def _seleccionar_todo_busqueda(self):
        try:
            if hasattr(self, 'txt_busqueda') and self.txt_busqueda:
                self.txt_busqueda.SelectAll()
        except Exception:
            pass

    def on_busqueda_context_menu(self, event):
        menu = wx.Menu()
        item_paste = menu.Append(wx.ID_PASTE, "&Pegar enlace del portapapeles\tCtrl+V")
        menu.AppendSeparator()
        item_canal_vids = menu.Append(1081, "Explorar &vídeos de este canal (URL o @usuario)")
        item_canal_pls = menu.Append(1082, "Explorar &listas de reproducción de este canal")
        item_playlist = menu.Append(1083, "Explorar vídeos de esta &lista de reproducción")

        def _pegar(e):
            if wx.TheClipboard.Open():
                if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                    data = wx.TextDataObject()
                    wx.TheClipboard.GetData(data)
                    self.txt_busqueda.SetValue(data.GetText())
                wx.TheClipboard.Close()

        def _canal_v(e):
            url = self.txt_busqueda.GetValue().strip()
            if url:
                self.ejecutar_busqueda_canal_videos(url)

        def _canal_p(e):
            url = self.txt_busqueda.GetValue().strip()
            if url:
                self.ejecutar_busqueda_canal_playlists(url)

        def _playlist(e):
            url = self.txt_busqueda.GetValue().strip()
            if url:
                self.ejecutar_busqueda_playlist_videos(url)

        self.Bind(wx.EVT_MENU, _pegar, item_paste)
        self.Bind(wx.EVT_MENU, _canal_v, item_canal_vids)
        self.Bind(wx.EVT_MENU, _canal_p, item_canal_pls)
        self.Bind(wx.EVT_MENU, _playlist, item_playlist)

        self.PopupMenu(menu)
        menu.Destroy()



def main():
    app = wx.App(False)
    frame = MainFrame()
    frame.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
