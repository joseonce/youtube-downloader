"""
Mixin de menú, actualización y ciclo de vida de la ventana para MainFrame.
"""

import os
import sys
import webbrowser
import wx

import accessibility
import sound_manager
import updater
from config_manager import (
    abrir_manual_usuario,
    abrir_atajos_teclado,
    get_docs_dir,
    cargar_configuracion,
    get_external_ytdlp_exe,
    ENGINES_MAP
)
from streaming import _ensure_ytdlp
from favorites_manager import obtener_favoritos, es_favorito
from options_dialog import OptionsDialog
from misc_dialogs import UpdateDialog, ShortcutsDialog


class MainLifecycleMixin:
    def verificar_libreria_ytdlp(self, on_success=None):
        """
        Comprueba si el ejecutable yt-dlp.exe o la librería yt_dlp están disponibles.
        Si no se encuentra ninguna, muestra el mensaje de aviso requerido y ofrece su descarga automática.
        """
        if get_external_ytdlp_exe() is not None or _ensure_ytdlp() is not None:
            if on_success:
                on_success()
            return True

        msg = "no se encuentra la librería necesaria para la ejecución del programa, se va a proceder a su descarga"
        accessibility.speak(msg)
        resp = wx.MessageBox(
            msg,
            "Descarga de componentes necesarios",
            wx.OK | wx.CANCEL | wx.ICON_WARNING,
            self
        )
        if resp == wx.OK:
            dlg = UpdateDialog(self, auto_start_download=True)
            dlg.ShowModal()
            dlg.Destroy()
            if get_external_ytdlp_exe() is not None or _ensure_ytdlp() is not None:
                if on_success:
                    on_success()
                return True
            else:
                self.set_status("No se pudo completar la descarga de la librería necesaria.", field=0, announce=True)
                return False
        else:
            self.set_status("Descarga cancelada. La aplicación requiere la librería para funcionar.", field=0, announce=True)
            return False

    def _init_menu(self):
        menubar = wx.MenuBar()
        
        # 1. Menú Archivo
        menu_archivo = wx.Menu()
        item_buscar = menu_archivo.Append(wx.ID_FIND, "&Buscar...\tCtrl+F")
        self.item_siguientes = menu_archivo.Append(1008, "Cargar &siguientes resultados\tCtrl+Shift+N")
        self.item_siguientes.Enable(False)
        menu_archivo.AppendSeparator()
        self.item_descargar = menu_archivo.Append(1001, "&Descargar selección\tCtrl+D")
        self.item_descargar_todo = menu_archivo.Append(1009, "Descargar &todos los vídeos de esta lista\tCtrl+Shift+D")
        item_abrir_carpeta = menu_archivo.Append(wx.ID_OPEN, "&Abrir carpeta de descargas\tCtrl+O")
        menu_archivo.AppendSeparator()
        item_salir = menu_archivo.Append(wx.ID_EXIT, "&Salir\tAlt+F4")

        # 2. Menú Edición
        menu_edicion = wx.Menu()
        self.item_sel_toggle = menu_edicion.Append(wx.ID_ANY, "&Marcar o desmarcar elemento actual (Espacio)")
        self.item_sel_all = menu_edicion.Append(wx.ID_SELECTALL, "&Seleccionar todos los elementos\tCtrl+A")
        self.item_desel_all = menu_edicion.Append(1020, "&Deseleccionar todos")
        self.item_inv_sel = menu_edicion.Append(1021, "&Invertir selección")
        menu_edicion.AppendSeparator()
        self.item_copiar = menu_edicion.Append(wx.ID_COPY, "&Copiar enlace al portapapeles\tCtrl+C")
        self.item_desc_ed = menu_edicion.Append(wx.ID_ANY, "Ver &descripción del elemento seleccionado...")
        self.item_canal_vids_ed = menu_edicion.Append(wx.ID_ANY, "&Mostrar vídeos del canal al que pertenece")
        self.item_canal_copy_ed = menu_edicion.Append(wx.ID_ANY, "Copiar &URL del canal al que pertenece")

        # 3. Menú Reproducción
        self.menu_reproduccion = wx.Menu()
        menu_reproduccion = self.menu_reproduccion
        self.item_previsualizar = menu_reproduccion.Append(wx.ID_PREVIEW, "&Ver / Reproducir selección...\tCtrl+P")
        self.item_play_all = menu_reproduccion.Append(1006, "&Reproducir toda la lista continua\tCtrl+L")
        menu_reproduccion.AppendSeparator()
        self.item_add_queue = menu_reproduccion.Append(1080, "Aña&dir a la cola de reproducción\tCtrl+Q")
        self.item_ver_cola = None
        self.item_play_queue = None
        self.item_vaciar_cola = None

        # 4. Menú Favoritos
        menu_favoritos = wx.Menu()
        self.item_ver_fav = menu_favoritos.Append(1004, "&Ver lista de favoritos...\tCtrl+H")
        self.item_play_fav = menu_favoritos.Append(1007, "&Reproducir lista de favoritos...\tCtrl+Shift+P")
        menu_favoritos.AppendSeparator()
        self.item_add_fav = menu_favoritos.Append(1005, "&Añadir o quitar selección de Favoritos\tCtrl+B")
        self.item_cambiar_fav = menu_favoritos.Append(1041, "C&ambiar de lista de favoritos...\tCtrl+M")
        self.item_eliminar_fav = menu_favoritos.Append(1040, "&Eliminar de Favoritos\tSupr")
        self.item_vaciar_fav = menu_favoritos.Append(1042, "&Vaciar lista de favoritos...")

        # 5. Menú Cuenta (YouTube / Google)
        menu_cuenta = wx.Menu()
        item_historial = menu_cuenta.Append(1050, "&Historial de reproducciones...\tCtrl+Shift+H")
        item_ver_mas_tarde = menu_cuenta.Append(1051, "Lista \"&Ver más tarde\"...\tCtrl+Shift+W")
        item_mis_playlists = menu_cuenta.Append(1052, "Mis &listas de reproducción...\tCtrl+Shift+Y")
        menu_cuenta.AppendSeparator()
        item_cfg_cuenta = menu_cuenta.Append(1053, "Configurar &sesión y cookies...")
        
        # 6. Menú Opciones
        menu_opciones = wx.Menu()
        item_preferencias = menu_opciones.Append(1030, "&Preferencias...\tCtrl+,")

        # 7. Menú Ayuda
        menu_ayuda = wx.Menu()
        item_manual = menu_ayuda.Append(wx.ID_HELP, "&Manual de usuario...\tF1")
        item_atajos = menu_ayuda.Append(1031, "&Atajos de teclado...\tShift+F1")
        item_act_app = menu_ayuda.Append(1032, "Comprobar actualizaciones del &programa...\tCtrl+Shift+U")
        item_actualizar = menu_ayuda.Append(1002, "&Actualizar yt-dlp (Versión Nightly)...\tCtrl+U")
        item_acerca = menu_ayuda.Append(wx.ID_ABOUT, "&Acerca de...")

        menubar.Append(menu_archivo, "&Archivo")
        menubar.Append(menu_edicion, "&Edición")
        menubar.Append(menu_reproduccion, "&Reproducción")
        menubar.Append(menu_favoritos, "&Favoritos")
        menubar.Append(menu_cuenta, "&Cuenta")
        menubar.Append(menu_opciones, "&Opciones")
        menubar.Append(menu_ayuda, "A&yuda")
        self.SetMenuBar(menubar)

        # Eventos del menú Archivo
        self.Bind(wx.EVT_MENU, lambda e: self.txt_busqueda.SetFocus(), item_buscar)
        self.Bind(wx.EVT_MENU, self.on_btn_siguientes, self.item_siguientes)
        self.Bind(wx.EVT_MENU, self.on_btn_descargar, self.item_descargar)
        self.Bind(wx.EVT_MENU, self.descargar_todos_los_videos_lista_actual, self.item_descargar_todo)
        self.Bind(wx.EVT_MENU, self.on_abrir_carpeta, item_abrir_carpeta)
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), item_salir)

        # Eventos del menú Edición
        self.Bind(wx.EVT_MENU, lambda e: self.toggle_seleccion_actual(), self.item_sel_toggle)
        self.Bind(wx.EVT_MENU, lambda e: self.seleccionar_todos(), self.item_sel_all)
        self.Bind(wx.EVT_MENU, lambda e: self.deseleccionar_todos(), self.item_desel_all)
        self.Bind(wx.EVT_MENU, lambda e: self.invertir_seleccion(), self.item_inv_sel)
        self.Bind(wx.EVT_MENU, self.on_copiar_enlace, self.item_copiar)
        self.Bind(wx.EVT_MENU, lambda e: self.mostrar_descripcion(), self.item_desc_ed)
        self.Bind(wx.EVT_MENU, lambda e: self.mostrar_videos_del_canal_seleccionado(), self.item_canal_vids_ed)
        self.Bind(wx.EVT_MENU, lambda e: self.copiar_url_del_canal_seleccionado(), self.item_canal_copy_ed)

        # Eventos del menú Reproducción
        self.Bind(wx.EVT_MENU, self.on_previsualizar_video, self.item_previsualizar)
        self.Bind(wx.EVT_MENU, self.reproducir_toda_la_lista, self.item_play_all)
        self.Bind(wx.EVT_MENU, self.agregar_a_cola_reproduccion, id=1080)
        self.Bind(wx.EVT_MENU, self.reproducir_cola, id=1081)
        self.Bind(wx.EVT_MENU, self.mostrar_dialogo_cola, id=1082)
        self.Bind(wx.EVT_MENU, self.vaciar_cola_reproduccion, id=1083)

        # Eventos del menú Favoritos
        self.Bind(wx.EVT_MENU, self.mostrar_favoritos, self.item_ver_fav)
        self.Bind(wx.EVT_MENU, self.reproducir_favoritos, self.item_play_fav)
        self.Bind(wx.EVT_MENU, self.toggle_favorito_seleccion, self.item_add_fav)
        self.Bind(wx.EVT_MENU, self.on_cambiar_favorito_lista, self.item_cambiar_fav)
        self.Bind(wx.EVT_MENU, self.eliminar_favorito_seleccion, self.item_eliminar_fav)
        self.Bind(wx.EVT_MENU, self.vaciar_favoritos, self.item_vaciar_fav)

        # Eventos del menú Cuenta
        self.Bind(wx.EVT_MENU, lambda e: self.ejecutar_busqueda_historial(), item_historial)
        self.Bind(wx.EVT_MENU, lambda e: self.ejecutar_busqueda_ver_mas_tarde(), item_ver_mas_tarde)
        self.Bind(wx.EVT_MENU, lambda e: self.ejecutar_busqueda_mis_playlists(), item_mis_playlists)
        self.Bind(wx.EVT_MENU, self.on_abrir_opciones, item_cfg_cuenta)

        # Eventos del menú Opciones
        self.Bind(wx.EVT_MENU, self.on_abrir_opciones, item_preferencias)

        # Eventos del menú Ayuda
        self.Bind(wx.EVT_MENU, self.on_abrir_manual, item_manual)
        self.Bind(wx.EVT_MENU, self.on_abrir_atajos, item_atajos)
        self.Bind(wx.EVT_MENU, self.on_actualizar_app, item_act_app)
        self.Bind(wx.EVT_MENU, self.on_actualizar_ytdlp, item_actualizar)
        self.Bind(wx.EVT_MENU, self.on_acerca_de, item_acerca)

        # Evento al abrir menús para actualizar atenuación / estados
        self.Bind(wx.EVT_MENU_OPEN, self.on_menu_open)

    def on_menu_open(self, event=None):
        self.actualizar_estados_interfaz()
        if event:
            event.Skip()

    def actualizar_estados_interfaz(self):
        """Actualiza el estado habilitado/atenuado de botones y menús según el contexto de la aplicación."""
        num_items = len(self.resultados) if hasattr(self, 'resultados') and self.resultados else 0
        num_cola = len(self.cola_reproduccion) if hasattr(self, 'cola_reproduccion') and self.cola_reproduccion else 0
        try:
            num_favs = len(obtener_favoritos())
        except Exception:
            num_favs = 0

        hay_multiples = (num_items > 1)
        hay_elementos = (num_items > 0)
        hay_cola = (num_cola > 0)
        hay_favs = (num_favs > 0)

        # 1. Botones principales
        if hasattr(self, 'btn_descargar'):
            self.btn_descargar.Enable(hay_elementos)
        if hasattr(self, 'btn_previsualizar'):
            self.btn_previsualizar.Enable(hay_elementos)
        if hasattr(self, 'btn_reproducir_todo'):
            self.btn_reproducir_todo.Enable(hay_multiples)
        if hasattr(self, 'btn_add_cola'):
            self.btn_add_cola.Enable(hay_elementos)
        if hasattr(self, 'btn_reproducir_cola'):
            self.btn_reproducir_cola.Show(hay_cola)
            self.btn_reproducir_cola.Enable(hay_cola)
        if hasattr(self, 'btn_ver_cola'):
            self.btn_ver_cola.Show(hay_cola)
            self.btn_ver_cola.Enable(hay_cola)
        if hasattr(self, 'row_ctrls') and self.row_ctrls:
            self.row_ctrls.Layout()

        # 2. Menú Archivo
        if hasattr(self, 'item_descargar'):
            self.item_descargar.Enable(hay_elementos)
        if hasattr(self, 'item_descargar_todo'):
            self.item_descargar_todo.Enable(hay_multiples)

        # 3. Menú Edición
        if hasattr(self, 'item_sel_toggle'):
            self.item_sel_toggle.Enable(hay_multiples)
        if hasattr(self, 'item_sel_all'):
            self.item_sel_all.Enable(hay_multiples)
        if hasattr(self, 'item_desel_all'):
            self.item_desel_all.Enable(hay_multiples)
        if hasattr(self, 'item_inv_sel'):
            self.item_inv_sel.Enable(hay_multiples)
        if hasattr(self, 'item_copiar'):
            self.item_copiar.Enable(hay_elementos)
        if hasattr(self, 'item_desc_ed'):
            self.item_desc_ed.Enable(hay_elementos)
        if hasattr(self, 'item_canal_vids_ed'):
            self.item_canal_vids_ed.Enable(hay_elementos)
        if hasattr(self, 'item_canal_copy_ed'):
            self.item_canal_copy_ed.Enable(hay_elementos)

        # 4. Menú Reproducción
        if hasattr(self, 'item_previsualizar'):
            self.item_previsualizar.Enable(hay_elementos)
        if hasattr(self, 'item_play_all'):
            self.item_play_all.Enable(hay_multiples)
        if hasattr(self, 'item_add_queue'):
            self.item_add_queue.Enable(hay_elementos)

        if hasattr(self, 'menu_reproduccion') and self.menu_reproduccion:
            has_ver = (self.menu_reproduccion.FindItemById(1082) is not None)
            if hay_cola and not has_ver:
                self.item_ver_cola = self.menu_reproduccion.Append(1082, "Ver &cola de reproducción...\tCtrl+J")
                self.item_play_queue = self.menu_reproduccion.Append(1081, "Reproducir &cola de reproducción\tCtrl+Shift+Q")
                self.item_vaciar_cola = self.menu_reproduccion.Append(1083, "&Vaciar cola de reproducción")
            elif not hay_cola and has_ver:
                for mid in (1082, 1081, 1083):
                    it = self.menu_reproduccion.FindItemById(mid)
                    if it:
                        self.menu_reproduccion.DestroyItem(it)
                self.item_ver_cola = None
                self.item_play_queue = None
                self.item_vaciar_cola = None

        # 5. Menú Favoritos
        if hasattr(self, 'item_play_fav'):
            self.item_play_fav.Enable(hay_favs)
        if hasattr(self, 'item_add_fav'):
            self.item_add_fav.Enable(hay_elementos)
        if hasattr(self, 'item_cambiar_fav'):
            self.item_cambiar_fav.Enable(hay_elementos)
        if hasattr(self, 'item_eliminar_fav'):
            is_fav_view = getattr(self, 'is_showing_favorites', False)
            cur = self._get_selected_video() if hasattr(self, '_get_selected_video') else None
            is_item_fav = bool(cur and (is_fav_view or es_favorito(cur.get('url') or cur.get('id', ''))))
            self.item_eliminar_fav.Enable(is_item_fav or is_fav_view)
        if hasattr(self, 'item_vaciar_fav'):
            self.item_vaciar_fav.Enable(hay_favs)

    def _set_engine_index(self, index):
        self.engine_idx = index
        self.current_engine = ENGINES_MAP.get(index, ('ytsearch', 'YouTube'))[0]
        nombre = ENGINES_MAP.get(index, ('ytsearch', 'YouTube'))[1]
        
        if hasattr(self, 'menu_items_engine') and 0 <= index < len(self.menu_items_engine):
            self.menu_items_engine[index].Check(True)
            
        if hasattr(self, 'choice_tipo_busqueda'):
            self.choice_tipo_busqueda.Enable(self.current_engine == 'ytsearch')
        
        self.set_status(f"Plataforma seleccionada: {nombre}", field=0, announce=True)
        if hasattr(self, 'txt_busqueda'):
            self.txt_busqueda.SetFocus()

    def on_abrir_opciones(self, event=None):
        dlg = OptionsDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self.config = cargar_configuracion()
            self.downloader.config = self.config
            sound_manager.set_audio_device(self.config.get('audio_output_device', ''))
            accessibility.set_modo_locuciones(self.config.get('modo_locuciones', 'auto'))
            self.destino_dir = self.config.get('destino_dir', self.destino_dir)
            
            saved_fmt = min(self.config.get('formato_idx', 0), self.choice_formato.GetCount() - 1)
            self.choice_formato.SetSelection(saved_fmt)
            
            self.set_status("Opciones y preferencias actualizadas.", field=0, announce=True)
        dlg.Destroy()

    def on_tipo_busqueda_changed(self, event=None):
        sel = self.choice_tipo_busqueda.GetSelection()
        tipo_str = self.choice_tipo_busqueda.GetString(sel)
        accessibility.speak(f"Tipo de búsqueda: {tipo_str}")

    def _init_shortcuts(self):
        """Tabla de aceleradores de teclado globales."""
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_NORMAL, wx.WXK_ESCAPE, 1060),
            (wx.ACCEL_CTRL, ord('F'), wx.ID_FIND),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('N'), 1008),
            (wx.ACCEL_NORMAL, wx.WXK_F3, 1008),
            (wx.ACCEL_CTRL, ord('P'), wx.ID_PREVIEW),
            (wx.ACCEL_CTRL, ord('L'), 1006),
            (wx.ACCEL_CTRL, ord('Q'), 1080),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('Q'), 1081),
            (wx.ACCEL_CTRL, ord('J'), 1082),
            (wx.ACCEL_CTRL, ord('H'), 1004),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('H'), 1050),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('W'), 1051),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('Y'), 1052),
            (wx.ACCEL_CTRL, ord('B'), 1005),
            (wx.ACCEL_CTRL, ord('M'), 1041),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('P'), 1007),
            (wx.ACCEL_CTRL, ord('D'), 1001),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('D'), 1009),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('U'), 1032),
            (wx.ACCEL_CTRL, ord('U'), 1002),
            (wx.ACCEL_CTRL, ord('C'), wx.ID_COPY),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('C'), wx.ID_COPY),
            (wx.ACCEL_CTRL, ord('O'), wx.ID_OPEN),
            (wx.ACCEL_CTRL, ord(','), 1030),
            (wx.ACCEL_NORMAL, wx.WXK_F1, wx.ID_HELP),
            (wx.ACCEL_SHIFT, wx.WXK_F1, 1031),
            (wx.ACCEL_NORMAL, wx.WXK_F2, 1030),
            (wx.ACCEL_NORMAL, wx.WXK_F8, 1070),
        ])
        self.SetAcceleratorTable(accel_tbl)
        self.Bind(wx.EVT_MENU, self.anunciar_porcentaje_descarga, id=1070)
        self.Bind(wx.EVT_MENU, self.retroceder_nivel_o_limpiar, id=1060)
        self.Bind(wx.EVT_MENU, self.on_btn_siguientes, id=1008)
        self.Bind(wx.EVT_MENU, self.on_previsualizar_video, id=wx.ID_PREVIEW)
        self.Bind(wx.EVT_MENU, self.on_btn_descargar, id=1001)
        self.Bind(wx.EVT_MENU, self.descargar_todos_los_videos_lista_actual, id=1009)
        self.Bind(wx.EVT_MENU, self.agregar_a_cola_reproduccion, id=1080)
        self.Bind(wx.EVT_MENU, self.reproducir_cola, id=1081)
        self.Bind(wx.EVT_MENU, self.mostrar_dialogo_cola, id=1082)
        self.Bind(wx.EVT_MENU, self.on_actualizar_app, id=1032)
        self.Bind(wx.EVT_MENU, self.on_actualizar_ytdlp, id=1002)
        self.Bind(wx.EVT_MENU, self.mostrar_favoritos, id=1004)
        self.Bind(wx.EVT_MENU, lambda e: self.ejecutar_busqueda_historial(), id=1050)
        self.Bind(wx.EVT_MENU, lambda e: self.ejecutar_busqueda_ver_mas_tarde(), id=1051)
        self.Bind(wx.EVT_MENU, lambda e: self.ejecutar_busqueda_mis_playlists(), id=1052)
        self.Bind(wx.EVT_MENU, self.toggle_favorito_seleccion, id=1005)
        self.Bind(wx.EVT_MENU, self.on_cambiar_favorito_lista, id=1041)
        self.Bind(wx.EVT_MENU, self.eliminar_favorito_seleccion, id=1040)
        self.Bind(wx.EVT_MENU, self.reproducir_toda_la_lista, id=1006)
        self.Bind(wx.EVT_MENU, self.reproducir_favoritos, id=1007)
        self.Bind(wx.EVT_MENU, self.on_abrir_opciones, id=1030)
        self.Bind(wx.EVT_MENU, self.on_abrir_atajos, id=1031)

    def on_actualizar_ytdlp(self, event):
        dlg = UpdateDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_abrir_manual(self, event=None):
        self.set_status("Abriendo manual de usuario en el navegador web...", field=0, announce=True)
        ok = abrir_manual_usuario()
        if not ok:
            dlg = ShortcutsDialog(self)
            dlg.ShowModal()
            dlg.Destroy()

    def on_abrir_atajos(self, event=None):
        self.set_status("Abriendo atajos de teclado en el navegador web...", field=0, announce=True)
        ok = abrir_atajos_teclado()
        if not ok:
            dlg = ShortcutsDialog(self)
            dlg.ShowModal()
            dlg.Destroy()

    def on_actualizar_app(self, event=None):
        """Comprueba interactivamente si hay una nueva versión de la aplicación."""
        updater.manual_check_for_updates(self)

    def on_acerca_de(self, event):
        info = wx.adv.AboutDialogInfo()
        info.SetName(updater.APP_NAME)
        info.SetVersion(updater.APP_VERSION)
        info.SetDescription(
            "Aplicación de escritorio accesible para buscar, reproducir en streaming continuo y descargar vídeos, audios,\n"
            "canales y listas de reproducción de YouTube y más de 2.000 plataformas multimedia soportadas mediante enlaces directos.\n\n"
            "Desarrollado por: José Manuel Fernández Cortés"
        )
        info.SetCopyright("(C) 2026 José Manuel Fernández Cortés")
        info.AddDeveloper("José Manuel Fernández Cortés")
        wx.adv.AboutBox(info)

    def on_frame_activate(self, event):
        """
        Al cambiar de tarea y volver a la aplicación mientras el reproductor está abierto,
        transfiere automáticamente el foco y eleva la ventana del reproductor para permitir
        su control directo con atajos (vídeo F11, pausa, volumen, etc.).
        """
        if event.GetActive():
            if hasattr(self, 'active_preview_dialog') and self.active_preview_dialog:
                dlg = self.active_preview_dialog
                if not getattr(dlg, '_is_closing', False):
                    try:
                        if dlg.IsShown():
                            wx.CallAfter(self._enfocar_reproductor_activo)
                    except Exception:
                        pass
        event.Skip()

    def _enfocar_reproductor_activo(self):
        """Eleva la ventana del reproductor activo y sitúa el foco en su control interactivo principal."""
        try:
            dlg = getattr(self, 'active_preview_dialog', None)
            if dlg and not getattr(dlg, '_is_closing', False) and dlg.IsShown():
                dlg.Raise()
                dlg.SetFocus()
                if hasattr(dlg, 'btn_play_pause') and dlg.btn_play_pause:
                    dlg.btn_play_pause.SetFocus()
        except Exception:
            pass

    def on_close_window(self, event):
        """
        Intercepta el evento wx.EVT_CLOSE para garantizar un apagado limpio:
        - Detiene y cancela procesos de descarga activos (yt-dlp.exe, ffmpeg.exe).
        - Detiene y libera recursos del reproductor VLC (player e instance) y timers.
        - Libera recursos del sistema de accesibilidad (lectores de pantalla).
        - Evita bloqueos en carpetas temporales de PyInstaller (_MEI...).
        """
        if getattr(self, '_is_shutting_down', False):
            event.Skip()
            return

        # Confirmación si hay descargas activas
        descarga_activa = (
            self.btn_cancelar.IsEnabled() or
            (bool(self.cola_descargas) and self.indice_cola < len(self.cola_descargas))
        ) and not getattr(self.downloader, '_cancel_requested', False)
        if descarga_activa and event.CanVeto():
            resp = wx.MessageBox(
                "Hay descargas en curso. ¿Deseas cancelarlas y salir de la aplicación?",
                "Confirmar salida",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                self
            )
            if resp != wx.YES:
                event.Veto()
                return

        self._is_shutting_down = True

        # 1. Cancelar sonido de espera y procesos secundarios
        try:
            self.detener_sonido_espera()
        except Exception:
            pass

        try:
            self.downloader.request_cancel()
            proc = getattr(self.downloader, '_active_process', None)
            if proc:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=0.5)
                    except Exception:
                        proc.kill()
                except Exception:
                    pass
        except Exception:
            pass

        # 2. Detener y liberar el reproductor multimedia si está abierto
        try:
            if getattr(self, 'active_preview_dialog', None):
                dlg = self.active_preview_dialog
                self.active_preview_dialog = None
                dlg.on_cleanup()
                dlg.Destroy()
        except Exception:
            pass

        # 3. Liberar recursos de accesibilidad
        try:
            accessibility.shutdown_accessibility()
        except Exception:
            pass

        # 4. Forzar recolección de basura para soltar handles de DLLs/COM
        try:
            import gc
            gc.collect()
        except Exception:
            pass

        # 5. Desinicializar COM si estuvo activo (JAWS / SAPI)
        try:
            if 'pythoncom' in sys.modules:
                import pythoncom
                pythoncom.CoUninitialize()
        except Exception:
            pass

        event.Skip()

