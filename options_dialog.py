"""
Diálogo de Opciones y Preferencias de la aplicación.
Permite configurar rutas de descarga, formatos por defecto, parámetros de búsqueda,
reproducción, favoritos, dispositivos de audio exclusivos y modos de locución accesible.
"""

import os
import wx
import accessibility
import sound_manager
from config_manager import (
    cargar_configuracion,
    guardar_configuracion,
    MODOS_CARATULA
)
from ui_mpv import (
    obtener_dispositivos_audio,
    probar_dispositivo_audio
)


class OptionsDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Opciones y Preferencias", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.config = cargar_configuracion()
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Cuaderno de pestañas para organizar las secciones de configuración lógicamente
        self.notebook = wx.Notebook(self)
        
        # ==========================================
        # PESTAÑA 1: DESCARGAS Y FORMATOS
        # ==========================================
        tab_descargas = wx.Panel(self.notebook)
        sizer_descargas = wx.BoxSizer(wx.VERTICAL)
        
        # Grupo: Carpeta de descargas
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
        
        # Grupo: Formato de salida predeterminado para descargas
        box_format = wx.StaticBox(tab_descargas, label="Formato de salida predeterminado")
        sizer_format = wx.StaticBoxSizer(box_format, wx.VERTICAL)
        
        row_fmt = wx.BoxSizer(wx.HORIZONTAL)
        lbl_fmt = wx.StaticText(box_format, label="&Formato para descargas:")
        row_fmt.Add(lbl_fmt, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.formatos = [
            "Vídeo (Mejor calidad MP4)",
            "Audio MP3 (192 kbps - Estándar)",
            "Audio MP3 (320 kbps - Alta fidelidad)",
            "Audio M4A (Original AAC)",
            "Audio FLAC (Sin pérdida)",
            "Audio WAV (PCM sin comprimir)"
        ]
        self.choice_formato = wx.Choice(box_format, choices=self.formatos)
        self.choice_formato.SetSelection(min(self.config.get('formato_idx', 0), len(self.formatos) - 1))
        row_fmt.Add(self.choice_formato, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer_format.Add(row_fmt, 0, wx.EXPAND | wx.ALL, 8)
        
        sizer_descargas.Add(sizer_format, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Grupo: Carátula en descargas de audio y YouTube Music
        box_caratula = wx.StaticBox(tab_descargas, label="Carátula en descargas de audio y YouTube Music")
        sizer_caratula = wx.StaticBoxSizer(box_caratula, wx.VERTICAL)
        
        self.modos_caratula_keys = [m[0] for m in MODOS_CARATULA]
        opciones_caratula = [m[1] for m in MODOS_CARATULA]
        
        cfg_caratula = self.config.get('caratula_modo', 'incrustada')
        idx_caratula = self.modos_caratula_keys.index(cfg_caratula) if cfg_caratula in self.modos_caratula_keys else 0
        
        self.radio_caratula = wx.RadioBox(
            box_caratula,
            label="&Opciones de carátula para pistas de audio:",
            choices=opciones_caratula,
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS
        )
        self.radio_caratula.SetSelection(idx_caratula)
        sizer_caratula.Add(self.radio_caratula, 0, wx.EXPAND | wx.ALL, 6)
        
        sizer_descargas.Add(sizer_caratula, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Grupo: Comportamiento al finalizar descargas
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
        # PESTAÑA 2: BÚSQUEDA Y FAVORITOS
        # ==========================================
        tab_busqueda = wx.Panel(self.notebook)
        sizer_busqueda = wx.BoxSizer(wx.VERTICAL)
        
        # Parámetros de búsqueda
        box_defaults = wx.StaticBox(tab_busqueda, label="Parámetros de búsqueda")
        sizer_defaults = wx.StaticBoxSizer(box_defaults, wx.VERTICAL)
        
        row_max = wx.BoxSizer(wx.HORIZONTAL)
        lbl_max = wx.StaticText(box_defaults, label="&Cantidad de resultados por búsqueda:")
        row_max.Add(lbl_max, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.spin_max = wx.SpinCtrl(box_defaults, min=1, max=500, initial=self.config.get('max_results', 25), size=(80, -1))
        row_max.Add(self.spin_max, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_defaults.Add(row_max, 0, wx.EXPAND | wx.ALL, 8)
        
        sizer_busqueda.Add(sizer_defaults, 0, wx.EXPAND | wx.ALL, 8)

        # Gestión de Favoritos
        box_fav = wx.StaticBox(tab_busqueda, label="Gestión de Favoritos")
        sizer_fav = wx.StaticBoxSizer(box_fav, wx.VERTICAL)
        
        self.chk_confirm_delete_fav = wx.CheckBox(box_fav, label="&Pedir confirmación al eliminar un elemento de favoritos")
        self.chk_confirm_delete_fav.SetValue(self.config.get('confirmar_eliminar_favorito', True))
        sizer_fav.Add(self.chk_confirm_delete_fav, 0, wx.ALL, 6)
        
        sizer_busqueda.Add(sizer_fav, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        tab_busqueda.SetSizer(sizer_busqueda)
        self.notebook.AddPage(tab_busqueda, "Búsqueda y Favoritos")
        
        # ==========================================
        # PESTAÑA 3: REPRODUCCIÓN Y AUDIO
        # ==========================================
        tab_reprod = wx.Panel(self.notebook)
        sizer_reprod = wx.BoxSizer(wx.VERTICAL)
        
        box_player = wx.StaticBox(tab_reprod, label="Reproductor multimedia")
        sizer_player = wx.StaticBoxSizer(box_player, wx.VERTICAL)
        
        self.chk_play_video = wx.CheckBox(box_player, label="&Reproducir con vídeo por defecto (desmarcar para modo solo audio ultrarrápido)")
        self.chk_play_video.SetValue(self.config.get('reproducir_con_video', True))
        sizer_player.Add(self.chk_play_video, 0, wx.ALL, 6)

        self.chk_independent_window = wx.CheckBox(box_player, label="&Abrir reproductor en ventana independiente (permite seguir usando la app y añadir a la cola)")
        self.chk_independent_window.SetValue(self.config.get('reproductor_ventana_independiente', True))
        sizer_player.Add(self.chk_independent_window, 0, wx.ALL, 6)

        self.chk_auto_close_player = wx.CheckBox(box_player, label="&Cerrar la ventana del reproductor automáticamente al finalizar la reproducción")
        self.chk_auto_close_player.SetValue(self.config.get('cerrar_reproductor_al_finalizar', False))
        sizer_player.Add(self.chk_auto_close_player, 0, wx.ALL, 6)

        self.chk_normalize_volume = wx.CheckBox(
            box_player,
            label="&Normalizar volumen automáticamente (hace que todas las canciones suenen al mismo nivel)"
        )
        self.chk_normalize_volume.SetToolTip("Equilibra la sonoridad en tiempo real para evitar diferencias bruscas de volumen entre pistas.")
        self.chk_normalize_volume.SetValue(self.config.get('normalizar_volumen_reproductor', False))
        sizer_player.Add(self.chk_normalize_volume, 0, wx.ALL, 6)
        
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
        box_audio = wx.StaticBox(tab_reprod, label="Dispositivo de salida de audio exclusivo")
        sizer_audio = wx.StaticBoxSizer(box_audio, wx.VERTICAL)

        lbl_audio_info = wx.StaticText(
            box_audio,
            label="Altavoces o auriculares exclusivos para el reproductor (las locuciones TTS y lectores de pantalla no serán afectados):"
        )
        sizer_audio.Add(lbl_audio_info, 0, wx.ALL, 6)

        row_audio = wx.BoxSizer(wx.HORIZONTAL)
        lbl_audio = wx.StaticText(box_audio, label="&Dispositivo de salida:")
        row_audio.Add(lbl_audio, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        self.audio_devices = obtener_dispositivos_audio()
        self.choice_audio = wx.Choice(box_audio, choices=[d[1] for d in self.audio_devices])
        from ui_mpv import resolve_mpv_audio_device
        saved_dev = self.config.get('audio_output_device', '')
        resolved_saved = resolve_mpv_audio_device(saved_dev)
        sel_idx = 0
        for i, (d_id, _) in enumerate(self.audio_devices):
            if d_id == saved_dev or (d_id and d_id == resolved_saved):
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
        tab_reprod.SetSizer(sizer_reprod)
        self.notebook.AddPage(tab_reprod, "Reproducción y Audio")

        # ==========================================
        # PESTAÑA 4: ACCESIBILIDAD Y LOCUCIONES
        # ==========================================
        tab_accesibilidad = wx.Panel(self.notebook)
        sizer_accesibilidad = wx.BoxSizer(wx.VERTICAL)

        box_tts = wx.StaticBox(tab_accesibilidad, label="Locuciones de voz y lectores de pantalla")
        sizer_tts = wx.StaticBoxSizer(box_tts, wx.VERTICAL)

        lbl_tts_info = wx.StaticText(
            box_tts,
            label="Configura cuándo emitirá locuciones habladas la aplicación:\n"
                  "- Automático: solo emite si se detecta un lector de pantalla activo (NVDA, JAWS, Narrador).\n"
                  "- Siempre: lee siempre los anuncios usando la síntesis del sistema.\n"
                  "- Desactivado: desactiva las locuciones de voz adicionales."
        )
        sizer_tts.Add(lbl_tts_info, 0, wx.ALL, 8)

        row_tts = wx.BoxSizer(wx.HORIZONTAL)
        lbl_tts = wx.StaticText(box_tts, label="&Modo de locuciones:")
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
        sizer_tts.Add(row_tts, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        
        sizer_accesibilidad.Add(sizer_tts, 0, wx.EXPAND | wx.ALL, 8)
        tab_accesibilidad.SetSizer(sizer_accesibilidad)
        self.notebook.AddPage(tab_accesibilidad, "Accesibilidad y Locuciones")

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
        self.SetSize((660, 580))
        self.SetMinSize((600, 480))
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
        if hasattr(self, 'radio_caratula'):
            sel_caratula = self.radio_caratula.GetSelection()
            if 0 <= sel_caratula < len(self.modos_caratula_keys):
                self.config['caratula_modo'] = self.modos_caratula_keys[sel_caratula]
        self.config.pop('engine_idx', None)
        self.config.pop('search_type_idx', None)
        self.config['max_results'] = self.spin_max.GetValue()
        self.config['abrir_carpeta_al_terminar'] = self.chk_open_folder.GetValue()
        self.config['preguntar_abrir_carpeta'] = self.chk_ask_open_folder.GetValue()
        self.config['repetir_reproductor'] = self.chk_repeat.GetValue()
        self.config['aleatorio_reproductor'] = self.chk_shuffle.GetValue()
        self.config['reproducir_con_video'] = self.chk_play_video.GetValue()
        self.config['reproductor_ventana_independiente'] = self.chk_independent_window.GetValue()
        self.config['cerrar_reproductor_al_finalizar'] = self.chk_auto_close_player.GetValue()
        self.config['normalizar_volumen_reproductor'] = self.chk_normalize_volume.GetValue()
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
                parent.active_preview_dialog.set_audio_output_device(self.config.get('audio_output_device', ''))
                parent.active_preview_dialog.set_normalize_volume(self.config['normalizar_volumen_reproductor'])
            except Exception:
                pass

        # Modo de locuciones de voz
        sel_t = self.choice_tts.GetSelection()
        if 0 <= sel_t < len(self.modos_locuciones):
            modo_k = self.modos_locuciones[sel_t][0]
            self.config['modo_locuciones'] = modo_k
            accessibility.set_modo_locuciones(modo_k)

        guardar_configuracion(self.config)
        accessibility.speak("Opciones guardadas.")
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Close()
