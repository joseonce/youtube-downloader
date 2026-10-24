"""
Diálogo de configuración general y preferencias del usuario.
"""

import os
import sys
import threading
import wx

import accessibility
import sound_manager
from config_manager import (
    cargar_configuracion,
    guardar_configuracion,
    probar_conexion_sesion,
    get_cookie_args
)
from ui_vlc import obtener_dispositivos_audio, probar_dispositivo_audio

class OptionsDialog(wx.Dialog):
    """Diálogo accesible para configurar las opciones y preferencias generales del programa."""
    def __init__(self, parent):
        super().__init__(parent, title="Opciones y Preferencias", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.config = cargar_configuracion()
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Cuaderno de pestañas para organizar las secciones de configuración
        self.notebook = wx.Notebook(self)
        
        # ==========================================
        # PESTAÑA 1: DESCARGAS
        # ==========================================
        tab_descargas = wx.Panel(self.notebook)
        sizer_descargas = wx.BoxSizer(wx.VERTICAL)
        
        box_folder = wx.StaticBox(tab_descargas, label="Carpeta de descargas")
        sizer_folder = wx.StaticBoxSizer(box_folder, wx.VERTICAL)
        
        lbl_dir = wx.StaticText(box_folder, label="&Carpeta de destino predeterminada:")
        sizer_folder.Add(lbl_dir, 0, wx.LEFT | wx.TOP, 6)
        
        row_dir = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_destino = wx.TextCtrl(box_folder, value=self.config.get('destino_dir', os.path.expanduser('~')))
        row_dir.Add(self.txt_destino, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        
        self.btn_examinar = wx.Button(box_folder, label="&Examinar...")
        self.btn_examinar.Bind(wx.EVT_BUTTON, self.on_examinar)
        row_dir.Add(self.btn_examinar, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_folder.Add(row_dir, 0, wx.EXPAND | wx.ALL, 6)
        
        sizer_descargas.Add(sizer_folder, 0, wx.EXPAND | wx.ALL, 8)
        
        box_comp_desc = wx.StaticBox(tab_descargas, label="Comportamiento al finalizar descargas")
        sizer_comp_desc = wx.StaticBoxSizer(box_comp_desc, wx.VERTICAL)
        
        self.chk_open_folder = wx.CheckBox(box_comp_desc, label="&Abrir carpeta de descargas automáticamente al finalizar")
        self.chk_open_folder.SetValue(self.config.get('abrir_carpeta_al_terminar', False))
        self.chk_open_folder.Bind(wx.EVT_CHECKBOX, self.on_toggle_open_folder)
        sizer_comp_desc.Add(self.chk_open_folder, 0, wx.ALL, 6)

        self.chk_ask_open_folder = wx.CheckBox(box_comp_desc, label="&Preguntar si abrir la carpeta al finalizar la descarga (cuadro Sí / No)")
        self.chk_ask_open_folder.SetValue(self.config.get('preguntar_abrir_carpeta', True))
        self.chk_ask_open_folder.Enable(not self.chk_open_folder.GetValue())
        sizer_comp_desc.Add(self.chk_ask_open_folder, 0, wx.ALL, 6)

        self.chk_sonido_espera = wx.CheckBox(box_comp_desc, label="&Emitir un leve sonido de espera periódico mientras se procesa la descarga")
        self.chk_sonido_espera.SetValue(self.config.get('sonido_espera_descarga', True))
        sizer_comp_desc.Add(self.chk_sonido_espera, 0, wx.ALL, 6)
        
        sizer_descargas.Add(sizer_comp_desc, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        tab_descargas.SetSizer(sizer_descargas)
        self.notebook.AddPage(tab_descargas, "Descargas")
        
        # ==========================================
        # PESTAÑA 2: BÚSQUEDA Y FORMATOS
        # ==========================================
        tab_busqueda = wx.Panel(self.notebook)
        sizer_busqueda = wx.BoxSizer(wx.VERTICAL)
        
        box_defaults = wx.StaticBox(tab_busqueda, label="Parámetros de búsqueda y formato")
        sizer_defaults = wx.StaticBoxSizer(box_defaults, wx.VERTICAL)
        
        # Cantidad de resultados
        row_max = wx.BoxSizer(wx.HORIZONTAL)
        lbl_max = wx.StaticText(box_defaults, label="&Cantidad de resultados por búsqueda:")
        row_max.Add(lbl_max, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.spin_max = wx.SpinCtrl(box_defaults, min=1, max=500, initial=self.config.get('max_results', 25), size=(80, -1))
        row_max.Add(self.spin_max, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_defaults.Add(row_max, 0, wx.EXPAND | wx.ALL, 8)
        
        # Formato
        row_fmt = wx.BoxSizer(wx.HORIZONTAL)
        lbl_fmt = wx.StaticText(box_defaults, label="&Formato de salida predeterminado:")
        row_fmt.Add(lbl_fmt, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.formatos = [
            "Vídeo (Mejor calidad MP4)",
            "Audio MP3 (192 kbps - Estándar)",
            "Audio MP3 (320 kbps - Alta fidelidad)",
            "Audio M4A (Original AAC)",
            "Audio FLAC (Sin pérdida)",
            "Audio WAV (PCM sin comprimir)"
        ]
        self.choice_formato = wx.Choice(box_defaults, choices=self.formatos)
        self.choice_formato.SetSelection(min(self.config.get('formato_idx', 0), len(self.formatos) - 1))
        row_fmt.Add(self.choice_formato, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer_defaults.Add(row_fmt, 0, wx.EXPAND | wx.ALL, 8)
        
        sizer_busqueda.Add(sizer_defaults, 0, wx.EXPAND | wx.ALL, 8)
        tab_busqueda.SetSizer(sizer_busqueda)
        self.notebook.AddPage(tab_busqueda, "Búsqueda y Formatos")
        
        # ==========================================
        # PESTAÑA 3: REPRODUCCIÓN Y FAVORITOS
        # ==========================================
        tab_reprod = wx.Panel(self.notebook)
        sizer_reprod = wx.BoxSizer(wx.VERTICAL)
        
        box_player = wx.StaticBox(tab_reprod, label="Reproductor multimedia")
        sizer_player = wx.StaticBoxSizer(box_player, wx.VERTICAL)
        
        self.chk_play_video = wx.CheckBox(box_player, label="&Reproducir con vídeo por defecto (desmarcar para modo solo audio ultrarrápido)")
        self.chk_play_video.SetValue(self.config.get('reproducir_con_video', True))
        sizer_player.Add(self.chk_play_video, 0, wx.ALL, 6)
        
        self.chk_repeat = wx.CheckBox(box_player, label="&Repetición continua activada por defecto en el reproductor")
        self.chk_repeat.SetValue(self.config.get('repetir_reproductor', False))
        sizer_player.Add(self.chk_repeat, 0, wx.ALL, 6)

        self.chk_shuffle = wx.CheckBox(box_player, label="Modo &aleatorio (Shuffle) activado por defecto en el reproductor")
        self.chk_shuffle.SetValue(self.config.get('aleatorio_reproductor', False))
        sizer_player.Add(self.chk_shuffle, 0, wx.ALL, 6)

        # Velocidad de reproducción predeterminada
        row_speed = wx.BoxSizer(wx.HORIZONTAL)
        lbl_speed = wx.StaticText(box_player, label="&Velocidad de reproducción por defecto:")
        row_speed.Add(lbl_speed, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.velocidades = [
            "0.5x", "0.6x", "0.7x", "0.8x", "0.9x", "1.0x (Normal)",
            "1.1x", "1.2x", "1.3x", "1.4x", "1.5x", "1.6x", "1.7x", "1.8x", "1.9x", "2.0x"
        ]
        self.velocidades_val = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]
        self.choice_speed = wx.Choice(box_player, choices=self.velocidades)
        cur_vel = round(float(self.config.get('velocidad_reproduccion', 1.0)), 1)
        try:
            vel_idx = self.velocidades_val.index(cur_vel)
        except ValueError:
            vel_idx = 5
        self.choice_speed.SetSelection(vel_idx)
        row_speed.Add(self.choice_speed, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer_player.Add(row_speed, 0, wx.EXPAND | wx.ALL, 6)
        
        sizer_reprod.Add(sizer_player, 0, wx.EXPAND | wx.ALL, 8)
        
        # Grupo de Dispositivo de salida de audio
        box_audio = wx.StaticBox(tab_reprod, label="Dispositivo de salida de audio")
        sizer_audio = wx.StaticBoxSizer(box_audio, wx.VERTICAL)

        lbl_audio_info = wx.StaticText(
            box_audio,
            label="Permite elegir los altavoces o auriculares exclusivos para el reproductor multimedia (las locuciones TTS y lectores de pantalla no serán afectados):"
        )
        sizer_audio.Add(lbl_audio_info, 0, wx.ALL, 6)

        row_audio = wx.BoxSizer(wx.HORIZONTAL)
        lbl_audio = wx.StaticText(box_audio, label="&Dispositivo de salida:")
        row_audio.Add(lbl_audio, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        self.audio_devices = obtener_dispositivos_audio()
        self.choice_audio = wx.Choice(box_audio, choices=[d[1] for d in self.audio_devices])
        saved_dev = self.config.get('audio_output_device', '')
        sel_idx = 0
        for i, (d_id, _) in enumerate(self.audio_devices):
            if d_id == saved_dev:
                sel_idx = i
                break
        self.choice_audio.SetSelection(sel_idx)
        self.choice_audio.Bind(wx.EVT_CHOICE, self.on_audio_device_changed)
        row_audio.Add(self.choice_audio, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        self.btn_probar_audio = wx.Button(box_audio, label="&Probar sonido")
        self.btn_probar_audio.Bind(wx.EVT_BUTTON, self.on_probar_audio)
        row_audio.Add(self.btn_probar_audio, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.btn_refrescar_audio = wx.Button(box_audio, label="&Actualizar")
        self.btn_refrescar_audio.Bind(wx.EVT_BUTTON, self.on_refrescar_audio)
        row_audio.Add(self.btn_refrescar_audio, 0, wx.ALIGN_CENTER_VERTICAL)

        sizer_audio.Add(row_audio, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        sizer_reprod.Add(sizer_audio, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Grupo de Locuciones y Accesibilidad
        box_tts = wx.StaticBox(tab_reprod, label="Locuciones de voz y lectores de pantalla")
        sizer_tts = wx.StaticBoxSizer(box_tts, wx.VERTICAL)

        lbl_tts_info = wx.StaticText(
            box_tts,
            label="Permite configurar cuándo emitirá locuciones de voz la aplicación (los usuarios que ven pueden mantenerlo en Automático o Desactivado):"
        )
        sizer_tts.Add(lbl_tts_info, 0, wx.ALL, 6)

        row_tts = wx.BoxSizer(wx.HORIZONTAL)
        lbl_tts = wx.StaticText(box_tts, label="&Locuciones de voz:")
        row_tts.Add(lbl_tts, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        self.modos_locuciones = [
            ("auto", "Automático (solo si se detecta un lector de pantalla activo - Recomendado)"),
            ("siempre", "Siempre activadas (usar voz de Windows si no hay lector)"),
            ("desactivado", "Desactivadas (sin locuciones de voz)")
        ]
        self.choice_tts = wx.Choice(box_tts, choices=[m[1] for m in self.modos_locuciones])
        cur_modo = self.config.get('modo_locuciones', 'auto')
        sel_m = 0
        for i, (k, _) in enumerate(self.modos_locuciones):
            if k == cur_modo:
                sel_m = i
                break
        self.choice_tts.SetSelection(sel_m)
        row_tts.Add(self.choice_tts, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer_tts.Add(row_tts, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        sizer_reprod.Add(sizer_tts, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        box_fav = wx.StaticBox(tab_reprod, label="Favoritos")
        sizer_fav = wx.StaticBoxSizer(box_fav, wx.VERTICAL)
        
        self.chk_confirm_delete_fav = wx.CheckBox(box_fav, label="&Pedir confirmación al eliminar un elemento de favoritos")
        self.chk_confirm_delete_fav.SetValue(self.config.get('confirmar_eliminar_favorito', True))
        sizer_fav.Add(self.chk_confirm_delete_fav, 0, wx.ALL, 6)
        
        sizer_reprod.Add(sizer_fav, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        tab_reprod.SetSizer(sizer_reprod)
        self.notebook.AddPage(tab_reprod, "Reproducción y Favoritos")
        
        # ==========================================
        # PESTAÑA 4: CUENTA Y SESIÓN
        # ==========================================
        tab_session = wx.Panel(self.notebook)
        sizer_session_tab = wx.BoxSizer(wx.VERTICAL)
        
        box_session = wx.StaticBox(tab_session, label="Cuenta y Sesión de YouTube (Listas privadas e Historial)")
        sizer_session = wx.StaticBoxSizer(box_session, wx.VERTICAL)

        lbl_info_session = wx.StaticText(
            box_session,
            label="Permite acceder a tu historial, listas privadas y 'Ver más tarde' usando tu sesión activa de YouTube."
        )
        sizer_session.Add(lbl_info_session, 0, wx.ALL, 6)

        row_src = wx.BoxSizer(wx.HORIZONTAL)
        lbl_src = wx.StaticText(box_session, label="&Origen de la sesión:")
        row_src.Add(lbl_src, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        self.cookie_sources = [
            ("none", "Desactivado (Acceso público estándar)"),
            ("browser", "Navegador web (Firefox, Chrome, Edge, Brave...)"),
            ("file", "Archivo de cookies (cookies.txt exportado)")
        ]
        self.choice_cookie_src = wx.Choice(box_session, choices=[s[1] for s in self.cookie_sources])
        cur_src = self.config.get('cookie_source', 'none')
        cur_src_idx = 0
        for i, (k, _) in enumerate(self.cookie_sources):
            if k == cur_src:
                cur_src_idx = i
                break
        self.choice_cookie_src.SetSelection(cur_src_idx)
        self.choice_cookie_src.Bind(wx.EVT_CHOICE, self.on_cookie_src_changed)
        row_src.Add(self.choice_cookie_src, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer_session.Add(row_src, 0, wx.EXPAND | wx.ALL, 6)

        # Fila Navegador
        self.row_browser = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_browser = wx.StaticText(box_session, label="&Navegador:")
        self.row_browser.Add(self.lbl_browser, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.browsers = [
            ("firefox", "Firefox (Recomendado directo en Windows)"),
            ("chrome", "Google Chrome"),
            ("edge", "Microsoft Edge"),
            ("brave", "Brave"),
            ("opera", "Opera"),
            ("vivaldi", "Vivaldi")
        ]
        self.choice_browser = wx.Choice(box_session, choices=[b[1] for b in self.browsers])
        cur_b = self.config.get('cookie_browser', 'firefox')
        b_idx = 0
        for i, (k, _) in enumerate(self.browsers):
            if k == cur_b:
                b_idx = i
                break
        self.choice_browser.SetSelection(b_idx)
        self.row_browser.Add(self.choice_browser, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer_session.Add(self.row_browser, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        # Fila Archivo cookies.txt
        self.row_file = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_file = wx.StaticText(box_session, label="&Archivo cookies.txt:")
        self.row_file.Add(self.lbl_file, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.txt_cookie_file = wx.TextCtrl(box_session, value=self.config.get('cookie_file', ''))
        self.row_file.Add(self.txt_cookie_file, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.btn_examinar_cookies = wx.Button(box_session, label="&Examinar...")
        self.btn_examinar_cookies.Bind(wx.EVT_BUTTON, self.on_examinar_cookies)
        self.row_file.Add(self.btn_examinar_cookies, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_session.Add(self.row_file, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        # Fila Probar Sesión
        row_test = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_probar_sesion = wx.Button(box_session, label="&Probar conexión con YouTube...")
        self.btn_probar_sesion.Bind(wx.EVT_BUTTON, self.on_probar_sesion)
        row_test.Add(self.btn_probar_sesion, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.lbl_estado_sesion = wx.StaticText(box_session, label="")
        row_test.Add(self.lbl_estado_sesion, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer_session.Add(row_test, 0, wx.EXPAND | wx.ALL, 6)

        sizer_session_tab.Add(sizer_session, 0, wx.EXPAND | wx.ALL, 8)
        tab_session.SetSizer(sizer_session_tab)
        self.notebook.AddPage(tab_session, "Cuenta y Sesión")

        # Añadir el Notebook al Sizer principal
        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 8)
        
        # Botones Guardar y Cancelar
        row_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_save = wx.Button(self, wx.ID_OK, "&Guardar")
        btn_save.SetDefault()
        btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        row_btns.Add(btn_save, 0, wx.RIGHT, 8)
        
        btn_cancel = wx.Button(self, wx.ID_CANCEL, "&Cancelar")
        row_btns.Add(btn_cancel, 0)
        
        main_sizer.Add(row_btns, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)
        
        self.SetSizer(main_sizer)
        self.on_cookie_src_changed()
        self.SetSize((640, 560))
        self.SetMinSize((580, 460))
        self.CenterOnParent()
        
    def on_toggle_open_folder(self, event):
        auto_open = self.chk_open_folder.GetValue()
        self.chk_ask_open_folder.Enable(not auto_open)

    def on_audio_device_changed(self, event=None):
        sel = self.choice_audio.GetSelection()
        if 0 <= sel < len(self.audio_devices):
            name = self.audio_devices[sel][1]
            accessibility.speak(f"Dispositivo para el reproductor: {name}")

    def on_probar_audio(self, event=None):
        sel = self.choice_audio.GetSelection()
        if 0 <= sel < len(self.audio_devices):
            dev_id, dev_name = self.audio_devices[sel]
            accessibility.speak(f"Probando reproductor multimedia en {dev_name}...")
            probar_dispositivo_audio(dev_id)

    def on_refrescar_audio(self, event=None):
        sel_prev = self.choice_audio.GetSelection()
        prev_id = self.audio_devices[sel_prev][0] if 0 <= sel_prev < len(self.audio_devices) else ''
        self.audio_devices = obtener_dispositivos_audio()
        self.choice_audio.Clear()
        for _, name in self.audio_devices:
            self.choice_audio.Append(name)
        new_sel = 0
        for i, (d_id, _) in enumerate(self.audio_devices):
            if d_id == prev_id:
                new_sel = i
                break
        self.choice_audio.SetSelection(new_sel)
        accessibility.speak(f"Dispositivos de audio para reproductor actualizados. {len(self.audio_devices)} disponibles.")

    def on_cookie_src_changed(self, event=None):
        sel = self.choice_cookie_src.GetSelection()
        src_key = self.cookie_sources[sel][0]
        is_browser = (src_key == 'browser')
        is_file = (src_key == 'file')
        self.lbl_browser.Enable(is_browser)
        self.choice_browser.Enable(is_browser)
        self.lbl_file.Enable(is_file)
        self.txt_cookie_file.Enable(is_file)
        self.btn_examinar_cookies.Enable(is_file)
        self.btn_probar_sesion.Enable(src_key != 'none')
        if event:
            lbl = self.cookie_sources[sel][1]
            accessibility.speak(f"Origen de sesión: {lbl}")

    def on_examinar_cookies(self, event):
        wildcard = "Archivos de cookies (*.txt)|*.txt|Todos los archivos (*.*)|*.*"
        dlg = wx.FileDialog(self, "Seleccionar archivo cookies.txt", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.txt_cookie_file.SetValue(path)
            accessibility.speak(f"Archivo de cookies seleccionado: {os.path.basename(path)}")
        dlg.Destroy()

    def on_probar_sesion(self, event):
        sel = self.choice_cookie_src.GetSelection()
        src_key = self.cookie_sources[sel][0]
        if src_key == 'none':
            self.lbl_estado_sesion.SetLabel("Sesión desactivada.")
            accessibility.speak("Sesión desactivada.")
            return

        b_sel = self.choice_browser.GetSelection()
        b_key = self.browsers[b_sel][0]
        f_val = self.txt_cookie_file.GetValue().strip()

        cfg_test = {
            'cookie_source': src_key,
            'cookie_browser': b_key,
            'cookie_file': f_val
        }

        self.btn_probar_sesion.Enable(False)
        self.lbl_estado_sesion.SetLabel("Verificando sesión con YouTube...")
        accessibility.speak("Comprobando sesión con YouTube...")

        def _worker():
            ok, msg = probar_conexion_sesion(cfg_test)
            def _gui():
                self.btn_probar_sesion.Enable(True)
                if ok:
                    self.lbl_estado_sesion.SetLabel("¡Conexión correcta!")
                    accessibility.speak("Conexión con YouTube correcta. Sesión activa.")
                    wx.MessageBox(msg, "Comprobación de sesión", wx.OK | wx.ICON_INFORMATION, self)
                else:
                    self.lbl_estado_sesion.SetLabel("Error en la conexión.")
                    accessibility.speak("Error al verificar la sesión.")
                    wx.MessageBox(msg, "Error de sesión", wx.OK | wx.ICON_WARNING, self)
            wx.CallAfter(_gui)

        threading.Thread(target=_worker, daemon=True).start()

    def on_examinar(self, event):
        cur = self.txt_destino.GetValue().strip() or os.path.expanduser('~')
        dlg = wx.DirDialog(self, "Seleccionar carpeta de descargas predeterminada", defaultPath=cur)
        if dlg.ShowModal() == wx.ID_OK:
            self.txt_destino.SetValue(dlg.GetPath())
        dlg.Destroy()
        
    def on_save(self, event):
        path = self.txt_destino.GetValue().strip()
        if path:
            self.config['destino_dir'] = path
        self.config['formato_idx'] = self.choice_formato.GetSelection()
        self.config.pop('engine_idx', None)
        self.config.pop('search_type_idx', None)
        self.config['max_results'] = self.spin_max.GetValue()
        self.config['abrir_carpeta_al_terminar'] = self.chk_open_folder.GetValue()
        self.config['preguntar_abrir_carpeta'] = self.chk_ask_open_folder.GetValue()
        self.config['repetir_reproductor'] = self.chk_repeat.GetValue()
        self.config['aleatorio_reproductor'] = self.chk_shuffle.GetValue()
        self.config['reproducir_con_video'] = self.chk_play_video.GetValue()
        self.config['velocidad_reproduccion'] = self.velocidades_val[self.choice_speed.GetSelection()]
        self.config['confirmar_eliminar_favorito'] = self.chk_confirm_delete_fav.GetValue()
        self.config['sonido_espera_descarga'] = self.chk_sonido_espera.GetValue()

        # Dispositivo de salida de audio
        sel_a = self.choice_audio.GetSelection()
        if 0 <= sel_a < len(self.audio_devices):
            self.config['audio_output_device'] = self.audio_devices[sel_a][0]
            self.config['audio_output_device_name'] = self.audio_devices[sel_a][1]
            sound_manager.set_audio_device(self.audio_devices[sel_a][0])
            parent = self.GetParent()
            if hasattr(parent, 'active_preview_dialog') and parent.active_preview_dialog:
                try:
                    parent.active_preview_dialog.set_audio_output_device(self.config['audio_output_device'])
                except Exception:
                    pass

        # Modo de locuciones de voz
        sel_t = self.choice_tts.GetSelection()
        if 0 <= sel_t < len(self.modos_locuciones):
            modo_k = self.modos_locuciones[sel_t][0]
            self.config['modo_locuciones'] = modo_k
            accessibility.set_modo_locuciones(modo_k)

        sel_c = self.choice_cookie_src.GetSelection()
        self.config['cookie_source'] = self.cookie_sources[sel_c][0]
        sel_b = self.choice_browser.GetSelection()
        self.config['cookie_browser'] = self.browsers[sel_b][0]
        self.config['cookie_file'] = self.txt_cookie_file.GetValue().strip()
        guardar_configuracion(self.config)
        accessibility.speak("Opciones guardadas.")
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Close()

