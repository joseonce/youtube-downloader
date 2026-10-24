"""
Módulo del diálogo de reproducción multimedia con integración VLC y soporte de vídeo/audio.
"""

import os
import random
import sys
import time
import threading
import wx

import accessibility
import sound_manager
from config_manager import cargar_configuracion, guardar_configuracion
from streaming import obtener_url_streaming, precargar_stream_en_segundo_plano
from media_utils import formatear_duracion, formatear_visitas, limpiar_extension_titulo
from ui_vlc import vlc, get_vlc_module, init_vlc_env
from player_controls_mixin import PlayerControlsMixin


class ProgressBarSlider(wx.Slider):
    """
    Control deslizante para la barra de progreso de reproducción.
    No es alcanzable mediante el tabulador (excluido de la navegación por teclado),
    ya que está concebido para visualización y arrastre con ratón por personas videntes,
    mientras que las personas usuarias de lectores de pantalla y teclado emplean
    los atajos dedicados (Flechas izquierda/derecha, F9/F10, Espacio, etc.).
    """
    def AcceptsFocus(self):
        return False

    def AcceptsFocusFromKeyboard(self):
        return False


class VideoCanvasPanel(wx.Panel):
    """Lienzo de dibujo de libvlc, excluido de la navegación por tabulador."""
    def AcceptsFocus(self):
        return False

    def AcceptsFocusFromKeyboard(self):
        return False



class VideoPreviewDialog(PlayerControlsMixin, wx.Dialog):
    def __init__(self, parent, video_data_or_list, initial_index=0):
        if isinstance(video_data_or_list, list):
            self.videos = list(video_data_or_list)
        else:
            self.videos = [video_data_or_list]

        self._original_videos = list(self.videos)

        # Configuración persistente de volumen, repetición y modo vídeo/audio
        cfg = cargar_configuracion()
        self.initial_vol = cfg.get('volumen', 80)
        self.repeat_mode = cfg.get('repetir_reproductor', False)
        self.shuffle_mode = cfg.get('aleatorio_reproductor', False)
        self.reproducir_con_video = cfg.get('reproducir_con_video', True)
        self.show_video = self.reproducir_con_video
        self.playback_speed = float(cfg.get('velocidad_reproduccion', 1.0))
        self.playback_speed = round(min(2.0, max(0.5, self.playback_speed)), 1)
        self.audio_output_device = cfg.get('audio_output_device', '')

        # Si el modo aleatorio está activado y hay más de 1 vídeo, decidimos primero el orden
        # de forma que no se repitan canciones durante la reproducción continua.
        if self.shuffle_mode and len(self.videos) > 1:
            import random
            if 0 < initial_index < len(self.videos):
                first_vid = self.videos[initial_index]
                resto = [v for i, v in enumerate(self.videos) if i != initial_index]
                random.shuffle(resto)
                self.videos = [first_vid] + resto
            else:
                random.shuffle(self.videos)
            self.current_index = 0
        else:
            self.current_index = max(0, min(initial_index, len(self.videos) - 1)) if self.videos else 0

        current_video = self.videos[self.current_index] if self.videos else {}

        super().__init__(
            parent,
            title=f"Reproductor: {current_video.get('title', 'Vídeo')}",
            size=(920, 680),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX
        )
        
        self._is_closing = False
        self.wants_download = False
        self.download_target_video = None
        self.is_dragging_slider = False

        # Diccionario para almacenar streams pre-obtenidos (url -> stream_url)
        self._prefetched_streams = {}
        self._prefetching_urls = set()
        self._prefetch_triggered = False
        self._prefetch_timer = None

        _vlc = get_vlc_module()
        if _vlc:
            try:
                self.vlc_instance = _vlc.Instance(
                    '--quiet', '--no-video-title-show',
                    '--network-caching=300',
                    '--file-caching=300',
                    '--live-caching=300'
                )
                self.vlc_player = self.vlc_instance.media_player_new()
                if self.audio_output_device:
                    try:
                        self.vlc_player.audio_output_device_set(None, self.audio_output_device)
                    except Exception:
                        pass
            except Exception:
                self.vlc_instance = None
                self.vlc_player = None
        else:
            self.vlc_instance = None
            self.vlc_player = None

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Barra superior con información del vídeo y posición en lista
        row_top = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_info = wx.StaticText(self, label="")
        self.lbl_info.SetFont(self.lbl_info.GetFont().Bold())
        row_top.Add(self.lbl_info, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        self.btn_fav = wx.Button(self, label="Favorito", size=(130, -1))
        self.btn_fav.Bind(wx.EVT_BUTTON, self.on_toggle_favorito)
        row_top.Add(self.btn_fav, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(row_top, 0, wx.ALL | wx.EXPAND, 8)

        # Lienzo nativo de vídeo (Panel con fondo negro sobre el que dibuja libvlc)
        self.video_panel = VideoCanvasPanel(self, size=(880, 440), style=wx.BORDER_SUNKEN)
        self.video_panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer.Add(self.video_panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        if not self.show_video:
            self.video_panel.Hide()

        # Barra de progreso y tiempo (excluida del tabulador, solo útil para videntes)
        row_seek = wx.BoxSizer(wx.HORIZONTAL)
        self.slider_pos = ProgressBarSlider(self, value=0, minValue=0, maxValue=1000, style=wx.SL_HORIZONTAL)
        self.slider_pos.Bind(wx.EVT_SCROLL_THUMBTRACK, self.on_slider_start_drag)
        self.slider_pos.Bind(wx.EVT_SCROLL_CHANGED, self.on_slider_seek)
        if sys.platform == 'win32':
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = self.slider_pos.GetHandle()
                if hwnd:
                    GWL_STYLE = -16
                    WS_TABSTOP = 0x00010000
                    st = user32.GetWindowLongW(hwnd, GWL_STYLE)
                    user32.SetWindowLongW(hwnd, GWL_STYLE, st & ~WS_TABSTOP)
            except Exception:
                pass
        self.slider_pos.Bind(wx.EVT_SET_FOCUS, lambda e: wx.CallAfter(self._redirigir_foco_desde_slider_pos))
        row_seek.Add(self.slider_pos, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        self.lbl_time = wx.StaticText(self, label="00:00 / --:--")
        row_seek.Add(self.lbl_time, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(row_seek, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        # Estado del reproductor
        self.lbl_status = wx.StaticText(self, label="Conectando con el flujo multimedia...")
        sizer.Add(self.lbl_status, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        # Barra de controles de reproducción nativa y accesible
        box_controls = wx.StaticBox(self, label="Controles de reproducción")
        sizer_controls = wx.StaticBoxSizer(box_controls, wx.HORIZONTAL)

        self.btn_prev = wx.Button(box_controls, label="Anterior (Ctrl+P)")
        self.btn_prev.SetToolTip("Pista anterior (Ctrl+P o Ctrl+Flecha Izquierda)")
        self.btn_prev.Bind(wx.EVT_BUTTON, lambda e: self.play_prev())
        sizer_controls.Add(self.btn_prev, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

        self.btn_play_pause = wx.Button(box_controls, label="Pausar")
        self.btn_play_pause.SetToolTip("Pausar o reanudar reproducción (P o Espacio)")
        self.btn_play_pause.SetDefault()
        self.btn_play_pause.Bind(wx.EVT_BUTTON, self.toggle_play_pause)
        sizer_controls.Add(self.btn_play_pause, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

        self.btn_stop = wx.Button(box_controls, label="Detener")
        self.btn_stop.SetToolTip("Detener reproducción (S)")
        self.btn_stop.Bind(wx.EVT_BUTTON, self.stop)
        sizer_controls.Add(self.btn_stop, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

        self.btn_next = wx.Button(box_controls, label="Siguiente (Ctrl+N)")
        self.btn_next.SetToolTip("Pista siguiente (Ctrl+N o Ctrl+Flecha Derecha)")
        self.btn_next.Bind(wx.EVT_BUTTON, lambda e: self.play_next())
        sizer_controls.Add(self.btn_next, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        self.btn_queue = wx.Button(box_controls, label="Ver cola (Q)")
        self.btn_queue.Show(len(self.videos) > 1)
        self.btn_queue.SetToolTip("Consultar y gestionar la cola de reproducción (Q)")
        self.btn_queue.Bind(wx.EVT_BUTTON, lambda e: self.abrir_dialogo_cola())
        sizer_controls.Add(self.btn_queue, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        # Control de volumen
        lbl_vol = wx.StaticText(box_controls, label="Volumen:")
        sizer_controls.Add(lbl_vol, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.slider_vol = wx.Slider(box_controls, value=self.initial_vol, minValue=0, maxValue=100, size=(100, -1))
        self.slider_vol.Bind(wx.EVT_SLIDER, self.on_volume_change)
        sizer_controls.Add(self.slider_vol, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.btn_mute = wx.Button(box_controls, label="Silenciar")
        self.btn_mute.Bind(wx.EVT_BUTTON, self.toggle_mute)
        sizer_controls.Add(self.btn_mute, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        self.btn_repeat = wx.Button(box_controls, label=f"Repetición: {'Activada' if self.repeat_mode else 'Desactivada'}")
        self.btn_repeat.Bind(wx.EVT_BUTTON, self.on_toggle_repeat)
        sizer_controls.Add(self.btn_repeat, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        self.btn_shuffle = wx.Button(box_controls, label=f"Aleatorio: {'Activado' if self.shuffle_mode else 'Desactivado'}")
        self.btn_shuffle.Bind(wx.EVT_BUTTON, self.on_toggle_shuffle)
        sizer_controls.Add(self.btn_shuffle, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        self.btn_toggle_video = wx.Button(box_controls, label=f"Vídeo: {'Activado' if self.show_video else 'Desactivado'} (F11)")
        self.btn_toggle_video.Bind(wx.EVT_BUTTON, self.toggle_video_display)
        sizer_controls.Add(self.btn_toggle_video, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        self.btn_download_current = wx.Button(box_controls, label="Descargar este vídeo")
        self.btn_download_current.Bind(wx.EVT_BUTTON, self.on_download_click)
        sizer_controls.Add(self.btn_download_current, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

        self.btn_copy_url = wx.Button(box_controls, label="Copiar enlace (Ctrl+Shift+C)")
        self.btn_copy_url.Bind(wx.EVT_BUTTON, self.copiar_enlace_actual)
        sizer_controls.Add(self.btn_copy_url, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

        self.btn_close = wx.Button(box_controls, id=wx.ID_CANCEL, label="Cerrar reproductor")
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_close_click)
        sizer_controls.Add(self.btn_close, 0, wx.ALIGN_CENTER_VERTICAL)
        self.SetEscapeId(wx.ID_CANCEL)

        sizer.Add(sizer_controls, 0, wx.EXPAND | wx.ALL, 8)

        self.SetSizer(sizer)
        if not self.show_video:
            self.SetSize((920, 260))
        self.CenterOnParent()

        # Atajos de teclado en el reproductor
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_hook)
        self.Bind(wx.EVT_CLOSE, self.on_window_close)
        self.Bind(wx.EVT_ACTIVATE, self.on_player_activate)

        # Cargar e iniciar la primera pista
        wx.CallAfter(self.load_and_play_current)
        if hasattr(self, 'btn_play_pause') and self.btn_play_pause:
            wx.CallAfter(self.btn_play_pause.SetFocus)
        if len(self.videos) > 1:
            wx.CallAfter(self._trigger_prefetch_pipeline)

    @property
    def video(self):
        if 0 <= self.current_index < len(self.videos):
            return self.videos[self.current_index]
        return {}


    def _update_ui_state(self):
        if getattr(self, '_is_closing', False):
            return
        total = len(self.videos)
        titulo = self.video.get('title', 'Vídeo')
        canal = self.video.get('channel', 'Desconocido')
        dur = self.video.get('duration', '--:--')

        try:
            self.SetTitle(f"Reproduciendo: {titulo}")
            self.lbl_info.SetLabel(f"{titulo}  —  {canal} ({dur})")

            self.btn_prev.Enable(self.current_index > 0 or self.repeat_mode)
            self.btn_next.Enable(self.current_index < total - 1 or self.repeat_mode)
            if hasattr(self, 'btn_queue') and self.btn_queue:
                hay_q = len(self.videos) > 1
                self.btn_queue.Show(hay_q)
                self.btn_queue.Enable(hay_q)

            vid_id_or_url = self.video.get('url') or self.video.get('id', '')
            if es_favorito(vid_id_or_url):
                self.btn_fav.SetLabel("En Favoritos")
            else:
                self.btn_fav.SetLabel("+ Favorito")
        except (RuntimeError, Exception):
            pass

    def load_and_play_current(self):
        if not self.videos or getattr(self, '_is_closing', False):
            return

        self._update_ui_state()
        self._prefetch_triggered = False
        if hasattr(self, '_prefetch_timer') and self._prefetch_timer and self._prefetch_timer.IsRunning():
            self._prefetch_timer.Stop()

        if not self.vlc_player:
            _vlc = get_vlc_module()
            if _vlc and not self.vlc_instance:
                try:
                    self.vlc_instance = _vlc.Instance(
                        '--quiet', '--no-video-title-show',
                        '--network-caching=300',
                        '--file-caching=300',
                        '--live-caching=300'
                    )
                    self.vlc_player = self.vlc_instance.media_player_new()
                    if self.audio_output_device:
                        try:
                            self.vlc_player.audio_output_device_set(None, self.audio_output_device)
                        except Exception:
                            pass
                except Exception:
                    self.vlc_player = None

        if not self.vlc_player:
            self.lbl_status.SetLabel("VLC no está disponible. Abriendo en el navegador...")
            accessibility.speak("VLC no está disponible. Abriendo en el navegador.")
            try:
                webbrowser.open(self.video.get('url', ''))
            except Exception:
                pass
            return

        # Vincular ventana nativa HWND de Windows si el vídeo está visible, o desvincularla si no
        if sys.platform.startswith('win'):
            if self.show_video:
                hwnd = self.video_panel.GetHandle()
                self.vlc_player.set_hwnd(hwnd)
            else:
                self.vlc_player.set_hwnd(0)

        if hasattr(self, 'timer') and self.timer.IsRunning():
            self.timer.Stop()

        # Detener la reproducción anterior de forma instantánea y no bloqueante:
        # set_media(None) libera el media actual sin el retraso que tiene stop().
        if self.vlc_player:
            try:
                self.vlc_player.set_media(None)
            except Exception:
                pass

        self.lbl_status.SetLabel("Obteniendo flujo multimedia...")
        accessibility.speak(f"Cargando: {self.video.get('title', 'Vídeo')}")

        target_url = self.video.get('url') or self.video.get('id', '')
        solo_audio = not self.show_video

        # Si ya teníamos la URL pre-cargada
        if target_url in self._prefetched_streams:
            stream_url = self._prefetched_streams[target_url]
            self._start_vlc_playback(stream_url)
            self._trigger_prefetch_pipeline()
            return

        def _fetch():
            try:
                # Si el prefetch en background ya está en curso para esta URL,
                # esperamos a que termine (hasta 15 s) antes de lanzar otra petición
                # redundante. Así el "salto manual" con N se beneficia del prefetch ya iniciado.
                import time as _time
                waited = 0.0
                while target_url in self._prefetching_urls and waited < 15.0:
                    _time.sleep(0.05)
                    waited += 0.05
                    if target_url in self._prefetched_streams:
                        break

                if target_url in self._prefetched_streams:
                    stream_url = self._prefetched_streams[target_url]
                else:
                    stream_url = obtener_url_streaming(target_url, solo_audio=solo_audio)
                    if stream_url:
                        self._prefetched_streams[target_url] = stream_url
                if not getattr(self, '_is_closing', False) and wx.GetApp():
                    wx.CallAfter(self._start_vlc_playback, stream_url)
                    wx.CallAfter(self._trigger_prefetch_pipeline)
            except Exception as e:
                if not getattr(self, '_is_closing', False) and wx.GetApp():
                    wx.CallAfter(self._on_play_error, str(e))

        threading.Thread(target=_fetch, daemon=True).start()

    def set_audio_output_device(self, dev_id):
        """Aplica dinámicamente el dispositivo de salida de audio seleccionado."""
        self.audio_output_device = dev_id or ''
        if self.vlc_player:
            try:
                self.vlc_player.audio_output_device_set(None, self.audio_output_device)
            except Exception:
                pass

    def _start_vlc_playback(self, stream_url):
        if getattr(self, '_is_closing', False) or not self.vlc_instance or not self.vlc_player:
            return
        if not stream_url:
            self._on_play_error("URL de transmisión no disponible.")
            return
        try:
            self._current_stream_url = stream_url
            media = self.vlc_instance.media_new(stream_url)
            media.add_option(':network-caching=300')
            if not self.show_video:
                media.add_option(':no-video')
            self.vlc_player.set_media(media)
            if self.audio_output_device:
                try:
                    self.vlc_player.audio_output_device_set(None, self.audio_output_device)
                except Exception:
                    pass
            if sys.platform.startswith('win'):
                if self.show_video:
                    hwnd = self.video_panel.GetHandle()
                    self.vlc_player.set_hwnd(hwnd)
                else:
                    self.vlc_player.set_hwnd(0)
            self.vlc_player.audio_set_volume(self.slider_vol.GetValue())
            self.vlc_player.play()
            if hasattr(self, 'playback_speed'):
                try:
                    self.vlc_player.set_rate(self.playback_speed)
                except Exception:
                    pass
            self.btn_play_pause.SetLabel("Pausar")
            tipo_str = "solo audio" if not self.show_video else "vídeo"
            self.lbl_status.SetLabel(f"Reproduciendo ({tipo_str}).")
            self.timer.Start(500)
            # Precarga predictiva inmediata de las siguientes pistas (pipeline)
            self._trigger_prefetch_pipeline()
        except Exception as e:
            self._on_play_error(str(e))

    def _on_play_error(self, err_msg):
        if getattr(self, '_is_closing', False):
            return
        try:
            if not self:
                return
            self.lbl_status.SetLabel("Error al obtener stream.")
            accessibility.speak("Error al reproducir el contenido.")
            wx.MessageBox(f"No se pudo reproducir el contenido:\n\n{err_msg}", "Error de reproducción", wx.OK | wx.ICON_ERROR, self)
        except Exception:
            pass

    def on_timer(self, event):
        if not self.vlc_player:
            return

        # Verificar si terminó el vídeo
        state = self.vlc_player.get_state()
        if state == vlc.State.Ended:
            self.on_track_finished()
            return

        length_ms = self.vlc_player.get_length()
        time_ms = self.vlc_player.get_time()

        if length_ms > 0 and time_ms >= 0:
            if not self.is_dragging_slider:
                pos_val = int((time_ms / length_ms) * 1000)
                self.slider_pos.SetValue(pos_val)

            cur_sec = int(time_ms / 1000)
            tot_sec = int(length_ms / 1000)
            self.lbl_time.SetLabel(f"{formatear_duracion(cur_sec)} / {formatear_duracion(tot_sec)}")

            # Asegurar pipeline de precarga activo
            rem_sec = tot_sec - cur_sec
            if rem_sec <= 25:
                self._trigger_prefetch_pipeline()

    def _trigger_prefetch_pipeline(self):
        """Precarga anticipada en segundo plano de las pistas siguientes (pipeline de 2 canciones adelante)."""
        if getattr(self, '_is_closing', False) or not self.videos:
            return
        total = len(self.videos)
        if total <= 1:
            return

        indices_a_precargar = []
        for offset in (1, 2):
            idx = self.current_index + offset
            if idx >= total:
                if self.repeat_mode:
                    idx = idx % total
                else:
                    continue
            if idx != self.current_index and idx not in indices_a_precargar:
                indices_a_precargar.append(idx)

        solo_audio = not self.show_video
        for idx in indices_a_precargar:
            vid = self.videos[idx]
            u = vid.get('url') or vid.get('id', '')
            if not u:
                continue
            if u in self._prefetched_streams or u in self._prefetching_urls:
                continue
            self._prefetching_urls.add(u)
            def _worker(target_u=u):
                try:
                    s_url = obtener_url_streaming(target_u, solo_audio=solo_audio)
                    if s_url:
                        self._prefetched_streams[target_u] = s_url
                except Exception:
                    pass
                finally:
                    self._prefetching_urls.discard(target_u)
            threading.Thread(target=_worker, daemon=True).start()

    def on_track_finished(self):
        total = len(self.videos)
        if self.current_index < total - 1:
            self.play_next()
        elif self.repeat_mode and total > 0:
            if getattr(self, 'shuffle_mode', False) and total > 1:
                import random
                shuffled = list(self.videos)
                random.shuffle(shuffled)
                self.videos = shuffled
            self.current_index = 0
            self.load_and_play_current()
        else:
            if hasattr(self, 'timer') and self.timer.IsRunning():
                self.timer.Stop()
            self.lbl_status.SetLabel("Fin de la lista de reproducción.")
            self.btn_play_pause.SetLabel("Reanudar")
            accessibility.speak("Fin de la lista de reproducción.")
            self.btn_play_pause.SetFocus()

    def play_next(self):
        total = len(self.videos)
        if total <= 1:
            return
        if self.current_index < total - 1:
            self.current_index += 1
            self.load_and_play_current()
        elif self.repeat_mode and total > 0:
            if getattr(self, 'shuffle_mode', False) and total > 1:
                import random
                shuffled = list(self.videos)
                random.shuffle(shuffled)
                self.videos = shuffled
            self.current_index = 0
            self.load_and_play_current()

    def play_prev(self):
        total = len(self.videos)
        if self.current_index > 0:
            self.current_index -= 1
            self.load_and_play_current()
        elif self.repeat_mode and total > 0:
            self.current_index = total - 1
            self.load_and_play_current()

    def agregar_a_cola(self, videos_o_video):
        """Añade uno o varios vídeos al final de la lista de reproducción continua."""
        if not isinstance(videos_o_video, list):
            videos_o_video = [videos_o_video]
        nuevos = [v for v in videos_o_video if v]
        if not nuevos:
            return len(self.videos)
        self.videos.extend(nuevos)
        if hasattr(self, '_original_videos'):
            self._original_videos.extend(nuevos)
        self._update_ui_state()
        self._trigger_prefetch_pipeline()
        return len(self.videos)

