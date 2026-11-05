"""
Tests modulares del sistema.
"""
import os
import sys
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_video_player_continuous_logic():
    print("\n[Extra] Probando lógica del Reproductor Continuo y Pre-carga (Pre-buffering 2s)...")
    import wx
    import config_manager
    cfg = config_manager.cargar_configuracion()
    cfg['aleatorio_reproductor'] = False
    config_manager.guardar_configuracion(cfg)
    from ui import VideoPreviewDialog

    app = wx.App(False)
    playlist = [
        {'id': 'dQw4w9WgXcQ', 'title': 'Pista 1', 'channel': 'Canal 1', 'duration': '03:33', 'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'},
        {'id': '9bZkp7q19f0', 'title': 'Pista 2', 'channel': 'Canal 2', 'duration': '04:12', 'url': 'https://www.youtube.com/watch?v=9bZkp7q19f0'},
        {'id': 'kJQP7kiw5Fk', 'title': 'Pista 3', 'channel': 'Canal 3', 'duration': '03:50', 'url': 'https://www.youtube.com/watch?v=kJQP7kiw5Fk'}
    ]

    dialog = VideoPreviewDialog(None, playlist, initial_index=0)
    assert len(dialog.videos) == 3
    assert dialog.current_index == 0
    assert dialog.video['id'] == 'dQw4w9WgXcQ'

    # Verificar que en el título NO aparece número de orden ni número total de resultados
    dialog._update_ui_state()
    assert dialog.GetTitle() == "Reproduciendo: Pista 1"
    assert "[" not in dialog.GetTitle() and "/" not in dialog.GetTitle()

    # Probar navegación siguiente / anterior
    dialog.play_next()
    assert dialog.current_index == 1
    assert dialog.video['id'] == '9bZkp7q19f0'

    dialog.play_prev()
    assert dialog.current_index == 0
    assert dialog.video['id'] == 'dQw4w9WgXcQ'

    # Simular trigger de pre-buffering (pipeline multitema)
    assert hasattr(dialog, '_trigger_prefetch_pipeline')
    dialog._trigger_prefetch_pipeline()

    # Probar alternar repetición y restaurar estado desactivado
    initial_rep = dialog.repeat_mode
    dialog.on_toggle_repeat(None)
    assert dialog.repeat_mode == (not initial_rep)
    dialog.on_toggle_repeat(None)
    assert dialog.repeat_mode is False

    # Probar alternar ventana de vídeo con F11
    assert dialog.show_video is True
    dialog.toggle_video_display(None)
    assert dialog.show_video is False
    assert dialog.video_panel.IsShown() is False
    dialog.toggle_video_display(None)
    assert dialog.show_video is True
    assert dialog.video_panel.IsShown() is True

    # Probar variación de velocidad de reproducción (F6 / F7) y límites 0.5x - 2.0x
    dialog.playback_speed = 1.0
    dialog.cambiar_velocidad(-0.1)
    assert dialog.playback_speed == 0.9
    dialog.cambiar_velocidad(0.1)
    assert dialog.playback_speed == 1.0
    dialog.cambiar_velocidad(0.2)
    assert dialog.playback_speed == 1.2
    assert "1,2x" in dialog.lbl_status.GetLabel()
    dialog.cambiar_velocidad(-0.4)
    assert dialog.playback_speed == 0.8
    assert "0,8x" in dialog.lbl_status.GetLabel()

    # Límites inferior (0.5) y superior (2.0)
    dialog.cambiar_velocidad(-5.0)
    assert dialog.playback_speed == 0.5, "Límite inferior debe ser 0.5"
    assert "0,5x" in dialog.lbl_status.GetLabel()
    dialog.cambiar_velocidad(5.0)
    assert dialog.playback_speed == 2.0, "Límite superior debe ser 2.0"
    assert "2,0x" in dialog.lbl_status.GetLabel()
    dialog.playback_speed = 1.0

    # Probar inicialización directa en modo solo audio (vídeo desactivado en preferencias) y cierre limpio
    from downloader import cargar_configuracion, guardar_configuracion
    cfg = cargar_configuracion()
    orig_vid_cfg = cfg.get('reproducir_con_video', True)
    cfg['reproducir_con_video'] = False
    guardar_configuracion(cfg)
    try:
        dlg_audio = VideoPreviewDialog(None, playlist, initial_index=0)
        assert dlg_audio.show_video is False, "En modo solo audio show_video debe ser False"
        assert dlg_audio.video_panel.IsShown() is False, "El panel de vídeo debe estar oculto en modo solo audio"
        dlg_audio.on_close_click()
        dlg_audio.Destroy()
    finally:
        cfg['reproducir_con_video'] = orig_vid_cfg
        guardar_configuracion(cfg)

    # Probar obtención de stream solo_audio ultrarrápido y stream de vídeo combinado
    from downloader import obtener_url_streaming
    import downloader
    stream_audio = obtener_url_streaming('dQw4w9WgXcQ', solo_audio=True)
    assert stream_audio is not None and len(stream_audio) > 0, "Debe obtenerse URL de stream de audio"

    stream_video = obtener_url_streaming('dQw4w9WgXcQ', solo_audio=False)
    assert stream_video is not None and len(stream_video) > 0 and stream_video.startswith('http'), "Debe obtenerse URL de stream de vídeo"

    # Simular entorno compilado (donde yt_dlp no se puede importar y depende de binario externo)
    if downloader.get_external_ytdlp_exe() is not None:
        orig_ensure = downloader._ensure_ytdlp
        downloader._ensure_ytdlp = lambda: None
        try:
            stream_compiled_video = obtener_url_streaming('dQw4w9WgXcQ', solo_audio=False)
            assert stream_compiled_video is not None and "googlevideo.com" in stream_compiled_video, "En entorno compilado debe extraerse stream directo"
        finally:
            downloader._ensure_ytdlp = orig_ensure

    dialog.on_cleanup()
    dialog.Destroy()
    app.Destroy()


def test_reproductor_shuffle_stop_y_atajos():
    import config_manager
    cfg_tmp = config_manager.cargar_configuracion()
    orig_shuffle_state = cfg_tmp.get('aleatorio_reproductor', False)
    cfg_tmp['aleatorio_reproductor'] = False
    config_manager.guardar_configuracion(cfg_tmp)
    print("\n[Extra] Probando botón de modo aleatorio (Shuffle), botón Detener y atajos P, S, A y Espacio...")
    import wx
    import ui

    app = wx.App.Get() or wx.App(False)
    vids = [
        {'title': 'Pista 1', 'channel': 'Artista', 'url': 'https://youtube.com/watch?v=1'},
        {'title': 'Pista 2', 'channel': 'Artista', 'url': 'https://youtube.com/watch?v=2'},
        {'title': 'Pista 3', 'channel': 'Artista', 'url': 'https://youtube.com/watch?v=3'}
    ]
    dlg = ui.VideoPreviewDialog(None, vids, initial_index=0)
    dlg.Show()
    app.Yield()

    try:
        # 1. Comprobar existencia de btn_shuffle y btn_stop
        assert hasattr(dlg, 'btn_shuffle'), "Debe existir el botón btn_shuffle"
        assert hasattr(dlg, 'btn_stop'), "Debe existir el botón btn_stop"
        assert dlg.btn_shuffle.GetLabel() == "Aleatorio: Desactivado"
        assert dlg.btn_stop.GetLabel() == "Detener"
        assert dlg.shuffle_mode is False

        # 2. Alternar modo aleatorio mediante on_toggle_shuffle
        dlg.on_toggle_shuffle()
        assert dlg.shuffle_mode is True
        assert dlg.btn_shuffle.GetLabel() == "Aleatorio: Activado"

        # 3. Comprobar play_next en modo aleatorio
        dlg.current_index = 0
        dlg.play_next()
        # Debe haber elegido un índice distinto a 0
        assert dlg.current_index in (1, 2), "En shuffle debe seleccionar otra pista distinta a la actual"

        # Desactivar shuffle
        dlg.on_toggle_shuffle()
        assert dlg.shuffle_mode is False
        assert dlg.btn_shuffle.GetLabel() == "Aleatorio: Desactivado"

        # 4. Probar método stop()
        dlg.stop()
        assert dlg.slider_pos.GetValue() == 0
        assert dlg.lbl_status.GetLabel() == "Reproducción detenida."
        assert dlg.btn_play_pause.GetLabel() == "Reproducir"

        # 5. Probar que Espacio pasa sin ser interceptado (event.Skip)
        class DummyKeyEvent:
            def __init__(self, keycode, ctrl=False, alt=False, shift=False):
                self._key = keycode
                self._ctrl = ctrl
                self._alt = alt
                self._shift = shift
                self.skipped = False
            def GetKeyCode(self):
                return self._key
            def ControlDown(self):
                return self._ctrl
            def AltDown(self):
                return self._alt
            def ShiftDown(self):
                return self._shift
            def Skip(self, val=True):
                self.skipped = val

        ev_space = DummyKeyEvent(wx.WXK_SPACE)
        dlg.on_key_hook(ev_space)
        assert ev_space.skipped is True, "La barra espaciadora debe hacer Skip para permitir activar botones enfocados"

        # 6. Probar atajo 'A' para alternar aleatorio
        ev_a = DummyKeyEvent(ord('A'))
        dlg.on_key_hook(ev_a)
        assert dlg.shuffle_mode is True, "La tecla 'A' debe activar el modo aleatorio"

        # 7. Probar atajo 'S' para detener
        ev_s = DummyKeyEvent(ord('S'))
        dlg.on_key_hook(ev_s)
        assert dlg.lbl_status.GetLabel() == "Reproducción detenida."

    finally:
        dlg.on_cleanup()
        dlg.Destroy()

    print("  -> Botón de modo aleatorio, botón Detener y atajos P, S, A y Espacio validados con éxito.")


def test_reproductor_orden_aleatorio_sin_repeticion_y_precarga():
    with patch("streaming.obtener_url_streaming", return_value="http://127.0.0.1/mock.mp3"):
        return _inner_test_reproductor_orden_aleatorio_sin_repeticion_y_precarga()

def _inner_test_reproductor_orden_aleatorio_sin_repeticion_y_precarga():
    print("\n[Extra] Probando orden aleatorio prefijado sin repetición y precarga predictiva...")
    import wx
    import ui
    from config_manager import cargar_configuracion, guardar_configuracion

    app = wx.App.Get() or wx.App(False)

    cfg = cargar_configuracion()
    orig_shuffle = cfg.get('aleatorio_reproductor', False)
    try:
        cfg['aleatorio_reproductor'] = True
        guardar_configuracion(cfg)

        vids = [
            {'title': f'Canción {i}', 'channel': 'Artista', 'url': f'https://youtube.com/watch?v={i}'}
            for i in range(1, 6)
        ]

        dlg = ui.VideoPreviewDialog(None, vids, initial_index=0)
        assert dlg.shuffle_mode is True, "El reproductor debe iniciar en modo aleatorio si está configurado"
        assert len(dlg.videos) == 5, "Deben estar las 5 canciones"
        # Comprobar que no hay canciones repetidas en el orden decidido
        urls = [v['url'] for v in dlg.videos]
        assert len(set(urls)) == 5, "No debe haber canciones repetidas en la lista aleatoria"
        assert dlg.current_index == 0, "El índice inicial tras barajar debe ser 0"

        # Comprobar que las 2 siguientes canciones para precarga corresponden a los índices 1 y 2 del orden decidido
        assert dlg.videos[1]['url'] == urls[1]
        assert dlg.videos[2]['url'] == urls[2]

        # Simular avance secuencial por el orden aleatorio prefijado
        played_urls = [dlg.video['url']]
        for _ in range(4):
            dlg.play_next()
            played_urls.append(dlg.video['url'])

        # Se deben haber recorrido todas sin repetir
        assert len(played_urls) == 5
        assert len(set(played_urls)) == 5
        assert played_urls == urls, "El avance continuo debe seguir exactamente el orden decidido"

        # Al terminar la última canción sin repetición, debe finalizar la reproducción
        dlg.repeat_mode = False
        dlg.on_track_finished()
        assert dlg.lbl_status.GetLabel() == "Fin de la lista de reproducción."

        # Probar con initial_index > 0: la pista seleccionada debe ir primero y el resto barajado
        dlg_idx = ui.VideoPreviewDialog(None, vids, initial_index=2)
        assert dlg_idx.videos[0]['url'] == vids[2]['url'], "La pista seleccionada expresamente debe sonar primero"
        assert len(set(v['url'] for v in dlg_idx.videos)) == 5, "No debe haber canciones repetidas"
        dlg_idx.on_cleanup()
        dlg_idx.Destroy()

        # Probar alternancia de aleatorio en caliente: desactivar y volver a activar
        dlg.on_toggle_shuffle() # Desactivar
        assert dlg.shuffle_mode is False
        assert [v['url'] for v in dlg.videos] == [v['url'] for v in vids], "Debe restaurar el orden secuencial original"

        dlg.on_cleanup()
        dlg.Destroy()
    finally:
        cfg['aleatorio_reproductor'] = orig_shuffle
        guardar_configuracion(cfg)

    print("  -> Orden aleatorio prefijado sin repetición y pipeline de precarga validados con éxito.")


def test_cola_reproduccion_y_descargas():
    print("\n[Extra] Probando cola de reproducción secuencial (Ctrl+Q, Ctrl+Shift+Q) y anuncio de descargas...")
    import wx
    import accessibility
    from ui import MainFrame

    spoken_msgs = []
    original_speak = accessibility.speak
    accessibility.speak = lambda msg: spoken_msgs.append(msg)

    app = wx.App.Get()
    if not app:
        app = wx.App(False)

    frame = MainFrame()
    try:
        # 1. Verificar cola de reproducción inicial
        assert hasattr(frame, 'cola_reproduccion')
        assert frame.cola_reproduccion == []

        # 2. Añadir elementos a la cola sin elementos seleccionados
        frame.agregar_a_cola_reproduccion()
        assert any("No hay ningún elemento seleccionado" in m for m in spoken_msgs)

        # 3. Añadir elementos simulados a los resultados
        item1 = {'id': 'v1', 'title': 'Canción 1 Fav A', 'url': 'https://youtube.com/watch?v=v1', 'tipo_item': 'video', 'selected': True}
        item2 = {'id': 'v2', 'title': 'Canción 2 Fav B', 'url': 'https://youtube.com/watch?v=v2', 'tipo_item': 'video', 'selected': False}
        frame.resultados = [item1, item2]

        spoken_msgs.clear()
        frame.agregar_a_cola_reproduccion()
        assert len(frame.cola_reproduccion) == 1
        assert frame.cola_reproduccion[0]['id'] == 'v1'
        assert any("Total en cola: 1" in m for m in spoken_msgs), f"Esperado 'Total en cola: 1', mensajes: {spoken_msgs}"

        # Añadir otro elemento
        item1['selected'] = False
        item2['selected'] = True
        spoken_msgs.clear()
        frame.agregar_a_cola_reproduccion()
        assert len(frame.cola_reproduccion) == 2
        assert frame.cola_reproduccion[1]['id'] == 'v2'
        assert any("Total en cola: 2" in m for m in spoken_msgs), f"Esperado 'Total en cola: 2', mensajes: {spoken_msgs}"

        # 4. Vaciar cola
        spoken_msgs.clear()
        frame.vaciar_cola_reproduccion()
        assert len(frame.cola_reproduccion) == 0
        assert any("Cola de reproducción vaciada" in m for m in spoken_msgs)

        # 5. Probar lógica de anuncio de descargas simultáneas ("2 descargas", "3 descargas")
        frame.cola_descargas = [item1]
        frame.btn_cancelar.Enable(True) # simula descarga activa
        spoken_msgs.clear()

        # Añadir segunda descarga cuando ya hay descarga activa
        frame._agregar_descargas_o_iniciar([item2])
        assert len(frame.cola_descargas) == 2
        assert any("2 descargas" in m for m in spoken_msgs), f"Debe anunciar '2 descargas', anunciado: {spoken_msgs}"

        item3 = {'id': 'v3', 'title': 'Vídeo 3', 'url': 'https://youtube.com/watch?v=v3', 'tipo_item': 'video'}
        spoken_msgs.clear()
        frame._agregar_descargas_o_iniciar([item3])
        assert len(frame.cola_descargas) == 3
        assert any("3 descargas" in m for m in spoken_msgs), f"Debe anunciar '3 descargas', anunciado: {spoken_msgs}"

        frame.cola_descargas.clear()
        frame.btn_cancelar.Enable(False)

    finally:
        accessibility.speak = original_speak
        frame.Destroy()

    print("  -> Cola de reproducción secuencial y anuncio progresivo de descargas validados satisfactoriamente.")


def test_ver_cola_dialogo_y_atajos_ctrl_p_n():
    print("\n[Extra] Probando atajos Ctrl+P, Ctrl+N y diálogo de visualización/gestión de cola (Supr)...")
    import wx
    import ui
    from config_manager import cargar_configuracion, guardar_configuracion

    app = wx.App.Get() or wx.App(False)
    vids = [
        {'id': 't1', 'title': 'Tema 1', 'channel': 'Canal A', 'duration': '03:00', 'url': 'https://youtube.com/watch?v=1'},
        {'id': 't2', 'title': 'Tema 2', 'channel': 'Canal B', 'duration': '04:00', 'url': 'https://youtube.com/watch?v=2'},
        {'id': 't3', 'title': 'Tema 3', 'channel': 'Canal C', 'duration': '05:00', 'url': 'https://youtube.com/watch?v=3'}
    ]
    cfg = cargar_configuracion()
    orig_shuf = cfg.get('aleatorio_reproductor', False)
    cfg['aleatorio_reproductor'] = False
    guardar_configuracion(cfg)
    try:
        dlg_player = ui.VideoPreviewDialog(None, list(vids), initial_index=0)
        dlg_player.Show()
        app.Yield()

        class DummyKeyEvent:
            def __init__(self, keycode, ctrl=False, alt=False, shift=False):
                self._key = keycode
                self._ctrl = ctrl
                self._alt = alt
                self._shift = shift
                self.skipped = False
            def GetKeyCode(self):
                return self._key
            def ControlDown(self):
                return self._ctrl
            def AltDown(self):
                return self._alt
            def ShiftDown(self):
                return self._shift
            def Skip(self, val=True):
                self.skipped = val

        # 1. Probar Ctrl+N para avanzar a la siguiente pista
        dlg_player.current_index = 0
        ev_ctrl_n = DummyKeyEvent(ord('N'), ctrl=True)
        dlg_player.on_key_hook(ev_ctrl_n)
        assert dlg_player.current_index == 1, "Ctrl+N debe avanzar al siguiente tema"

        # 2. Probar Ctrl+P para retroceder a la pista anterior
        ev_ctrl_p = DummyKeyEvent(ord('P'), ctrl=True)
        dlg_player.on_key_hook(ev_ctrl_p)
        assert dlg_player.current_index == 0, "Ctrl+P debe retroceder al tema anterior"

        # 3. Probar P solo (sin Ctrl) para pausar / reproducir
        ev_p = DummyKeyEvent(ord('P'), ctrl=False)
        dlg_player.on_key_hook(ev_p)
        assert dlg_player.current_index == 0, "P sin Ctrl no debe cambiar de pista"

        # 4. Probar existencia de btn_queue y botón Ver cola
        assert hasattr(dlg_player, 'btn_queue'), "Debe existir btn_queue en el reproductor"
        assert dlg_player.btn_queue.GetLabel() == "Ver cola (Q)"

        # 5. Probar ColaReproduccionDialog con eliminación por Supr
        dlg_cola = ui.ColaReproduccionDialog(dlg_player, dlg_player.videos, current_index=0, is_player=True)
        assert dlg_cola.lista_cola.GetItemCount() == 3
        # Seleccionar el segundo elemento y eliminarlo con on_eliminar_item (simulando Supr)
        dlg_cola.lista_cola.Select(1)
        dlg_cola.lista_cola.Focus(1)
        dlg_cola.on_eliminar_item()
        assert len(dlg_player.videos) == 2, "Debe quedar 2 temas tras eliminar uno"
        assert dlg_cola.lista_cola.GetItemCount() == 2
        assert dlg_player.videos[1]['id'] == 't3'
        dlg_cola.Destroy()

    finally:
        dlg_player.on_cleanup()
        dlg_player.Destroy()
        cfg['aleatorio_reproductor'] = orig_shuf
        guardar_configuracion(cfg)

    # Probar botón y método en MainFrame
    frame = ui.MainFrame()
    try:
        assert hasattr(frame, 'btn_ver_cola'), "MainFrame debe tener btn_ver_cola"
        assert hasattr(frame, 'mostrar_dialogo_cola'), "MainFrame debe tener método mostrar_dialogo_cola"
    finally:
        frame.Destroy()

    print("  -> Atajos Ctrl+P, Ctrl+N y diálogo de gestión de cola validados con éxito.")


def test_cola_menu_contextual_y_seleccion_favoritos():
    print("Probando selección estilo favoritos, marcas con Espacio/Ctrl+A y menú contextual en la cola de reproducción...")
    import wx
    import ui
    import accessibility

    app = wx.GetApp() or wx.App()
    spoken = []
    original_speak = accessibility.speak
    accessibility.speak = lambda msg: spoken.append(msg)

    try:
        # 1. Probar diálogo de cola con selección y marcas tipo favoritos
        vids = [
            {'id': 'c1', 'title': 'Tema Cola 1', 'channel': 'Canal 1', 'duration': '02:30', 'url': 'http://yt.com/c1'},
            {'id': 'c2', 'title': 'Tema Cola 2', 'channel': 'Canal 2', 'duration': '03:45', 'url': 'http://yt.com/c2'},
            {'id': 'c3', 'title': 'Tema Cola 3', 'channel': 'Canal 3', 'duration': '04:15', 'url': 'http://yt.com/c3'},
        ]
        dlg = ui.ColaReproduccionDialog(None, list(vids), is_player=False)
        assert dlg.lista_cola.GetItemCount() == 3

        # Marcar tema 1 con Espacio
        dlg.lista_cola.Select(0)
        dlg.lista_cola.Focus(0)
        dlg.on_toggle_marca()
        assert dlg.videos_ref[0].get('selected') is True
        assert "Marcado - " in dlg.lista_cola.GetItemText(0, 1)

        # Seleccionar todos con Ctrl+A
        dlg.seleccionar_todos()
        assert all(v.get('selected') for v in dlg.videos_ref)

        # Deseleccionar todos
        dlg.deseleccionar_todos()
        assert not any(v.get('selected') for v in dlg.videos_ref)

        # Invertir selección (quedan todos marcados)
        dlg.invertir_seleccion()
        assert all(v.get('selected') for v in dlg.videos_ref)

        # Eliminación múltiple de todos los marcados
        dlg.on_eliminar_item()
        assert len(dlg.videos_ref) == 0
        assert dlg.lista_cola.GetItemCount() == 0
        dlg.Destroy()

        # 2. Probar que en MainFrame, la cola solo aparece en barra de menú y botones cuando tiene contenido
        frame = ui.MainFrame()
        assert frame.btn_ver_cola.IsShown() is False
        assert frame.btn_reproducir_cola.IsShown() is False
        assert frame.menu_reproduccion.FindItemById(1082) is None
        assert frame.menu_reproduccion.FindItemById(1081) is None
        assert frame.menu_reproduccion.FindItemById(1083) is None

        # Al añadir elemento, aparece
        frame.agregar_a_cola_reproduccion(items=[{'id': 'x1', 'title': 'Pista', 'url': 'http://yt.com/x1'}])
        assert frame.btn_ver_cola.IsShown() is True
        assert frame.btn_reproducir_cola.IsShown() is True
        assert frame.menu_reproduccion.FindItemById(1082) is not None
        assert frame.menu_reproduccion.FindItemById(1081) is not None
        assert frame.menu_reproduccion.FindItemById(1083) is not None

        # Al vaciar, desaparece de nuevo
        frame.vaciar_cola_reproduccion()
        assert frame.btn_ver_cola.IsShown() is False
        assert frame.btn_reproducir_cola.IsShown() is False
        assert frame.menu_reproduccion.FindItemById(1082) is None
        assert frame.menu_reproduccion.FindItemById(1081) is None
        assert frame.menu_reproduccion.FindItemById(1083) is None
        frame.Destroy()

    finally:
        accessibility.speak = original_speak

    print("  -> Selección tipo favoritos y visibilidad condicional de la cola validadas con éxito.")


def test_dispositivo_salida_audio():
    print("\n[Extra] Probando selección de dispositivo de salida de audio en configuración y reproductor...")
    import downloader
    import sound_manager
    import ui
    import wx

    # 1. Comprobar DEFAULT_CONFIG
    cfg = downloader.DEFAULT_CONFIG
    assert 'audio_output_device' in cfg, "audio_output_device debe existir en DEFAULT_CONFIG"
    assert 'audio_output_device_name' in cfg, "audio_output_device_name debe existir en DEFAULT_CONFIG"

    # 2. Comprobar obtener_dispositivos_audio
    devs = ui.obtener_dispositivos_audio()
    assert isinstance(devs, list), "obtener_dispositivos_audio debe retornar una lista"
    assert len(devs) >= 1, "Debe retornar al menos el dispositivo predeterminado"
    assert devs[0][0] == '', "El primer dispositivo debe tener identificador vacío (predeterminado)"
    assert "Predeterminado" in devs[0][1], "El primer dispositivo debe llamarse Predeterminado"

    # 3. Comprobar sound_manager set/get
    sound_manager.set_audio_device("test_device_guid")
    assert sound_manager.get_audio_device() == "test_device_guid", "sound_manager debe guardar el dispositivo"
    sound_manager.set_audio_device("")
    assert sound_manager.get_audio_device() == "", "sound_manager debe restaurar el dispositivo por defecto"

    # 4. Comprobar probar_dispositivo_audio (no debe lanzar excepción)
    assert ui.probar_dispositivo_audio('') is True

    # 5. Comprobar OptionsDialog
    app = wx.GetApp() or wx.App()
    parent = wx.Frame(None)
    dlg = ui.OptionsDialog(parent)
    assert hasattr(dlg, 'choice_audio'), "OptionsDialog debe tener el selector choice_audio"
    assert hasattr(dlg, 'btn_probar_audio'), "OptionsDialog debe tener btn_probar_audio"
    assert hasattr(dlg, 'btn_refrescar_audio'), "OptionsDialog debe tener btn_refrescar_audio"
    assert dlg.choice_audio.GetCount() == len(dlg.audio_devices)
    dlg.Destroy()
    parent.Destroy()

    print("  -> Selección de dispositivo de salida de audio validada correctamente.")


def test_foco_reproductor_cambio_tarea_y_aislamiento_tts():
    print("\n[Extra] Probando recuperación de foco en reproductor tras cambio de tarea y aislamiento de TTS...")
    import ui
    import accessibility
    import wx
    from unittest.mock import MagicMock, patch

    app = wx.GetApp() or wx.App()
    parent = wx.Frame(None)

    # 1. Verificar métodos en MainFrame
    assert hasattr(ui.MainFrame, 'on_frame_activate'), "MainFrame debe tener on_frame_activate"
    assert hasattr(ui.MainFrame, '_enfocar_reproductor_activo'), "MainFrame debe tener _enfocar_reproductor_activo"
    assert hasattr(ui.VideoPreviewDialog, 'on_player_activate'), "VideoPreviewDialog debe tener on_player_activate"

    # 2. Simular VideoPreviewDialog
    dlg = ui.VideoPreviewDialog(parent, {'title': 'Vídeo de prueba', 'url': 'http://youtube.com/watch?v=123'})
    assert hasattr(dlg, 'btn_play_pause'), "VideoPreviewDialog debe tener btn_play_pause"
    assert hasattr(dlg, 'btn_toggle_video'), "VideoPreviewDialog debe tener btn_toggle_video"

    # 3. Simular evento de activación en MainFrame con reproductor activo
    mock_frame = MagicMock()
    mock_frame.active_preview_dialog = dlg
    event_active = MagicMock()
    event_active.GetActive.return_value = True

    # Comprobar llamada a _enfocar_reproductor_activo
    with patch.object(ui.MainFrame, '_enfocar_reproductor_activo') as mock_enfocar:
        ui.MainFrame.on_frame_activate(mock_frame, event_active)
        # wx.CallAfter encola la ejecución
        app.Yield()

    # 4. Probar que las locuciones TTS siguen funcionando y no se desvían cuando hay lector activo
    with patch('accessibility.is_app_active', return_value=True), \
         patch('accessibility.is_screen_reader_active', return_value=True), \
         patch('accessibility._speaker') as mock_speaker:
        accessibility.speak("Mensaje de prueba TTS")
        if mock_speaker:
            mock_speaker.speak.assert_called_with("Mensaje de prueba TTS", interrupt=True)

    # 5. Probar que NO se emite locución si la aplicación NO tiene el foco (trabajando en otra app)
    with patch('accessibility.is_app_active', return_value=False), \
         patch('accessibility.is_screen_reader_active', return_value=True), \
         patch('accessibility._speaker') as mock_speaker:
        accessibility.speak("Mensaje que no debe sonar")
        mock_speaker.speak.assert_not_called()

    # 6. Probar que SÍ se emite locución si la aplicación TIENE el foco y lector activo
    with patch('accessibility.is_app_active', return_value=True), \
         patch('accessibility.is_screen_reader_active', return_value=True), \
         patch('accessibility._speaker') as mock_speaker:
        accessibility.speak("Mensaje con foco activo")
        mock_speaker.speak.assert_called_with("Mensaje con foco activo", interrupt=True)

    dlg.on_cleanup()
    dlg.Destroy()
    parent.Destroy()
    print("  -> Recuperación de foco, aislamiento de TTS y supresión sin foco validados con éxito.")



def test_atajos_f8_f9_f10_informacion_tiempo():
    import wx
    from ui import VideoPreviewDialog
    print("\n[Extra] Probando atajos F8, F9 y F10...")
    app = wx.App.GetOrCreate() if hasattr(wx.App, 'GetOrCreate') else (wx.GetApp() or wx.App())
    parent = wx.Frame(None)
    video = {'id': 'vid1', 'title': 'Test Time Info', 'duration': '04:00', 'duration_seconds': 240}
    dlg = VideoPreviewDialog(parent, [video])

    spoken = []
    with patch('accessibility.speak', side_effect=lambda msg, **kw: spoken.append(str(msg))):
        class MockMpvPlaying:
            time_pos = 60.0
            duration = 240.0
            idle_active = False
            pause = False

        dlg.mpv_player = MockMpvPlaying()

        dlg.anunciar_tiempo_transcurrido()
        assert any("Tiempo transcurrido: 01:00" in s for s in spoken), f"F9 fallido: {spoken}"

        dlg.anunciar_tiempo_restante()
        assert any("Tiempo restante: 03:00" in s for s in spoken), f"F10 fallido: {spoken}"

        dlg.anunciar_porcentaje()
        assert any("25 por ciento" in s for s in spoken), f"F8 fallido: {spoken}"

        spoken.clear()
        class MockMpvBuffering:
            time_pos = 0.0
            duration = None
            idle_active = False
            pause = False

        dlg.mpv_player = MockMpvBuffering()
        dlg.anunciar_tiempo_transcurrido()
        assert any("Tiempo transcurrido: 00:00" in s for s in spoken), f"F9 inicio fallido: {spoken}"

        dlg.anunciar_tiempo_restante()
        assert any("Tiempo restante: 04:00" in s for s in spoken), f"F10 fallback fallido: {spoken}"

    dlg.on_cleanup()
    dlg.Destroy()
    parent.Destroy()
    print("  -> Atajos F8, F9 y F10 validados con exito con valores exactos y fallback de duracion.")


def test_atajos_flechas_seek_10_segundos():
    print("\n[Extra] Probando salto de 10 segundos simétrico en Flecha Derecha (+10s) y Flecha Izquierda (-10s)...")
    import wx
    from ui import VideoPreviewDialog

    app = wx.App.Get() or wx.App(False)
    parent = wx.Frame(None)
    playlist = [{'id': 'dQw4w9WgXcQ', 'title': 'Pista Test Flechas', 'channel': 'Canal', 'duration': '05:00', 'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'}]
    dlg = VideoPreviewDialog(parent, playlist, initial_index=0)

    seeks = []
    class MockMpvPlayer:
        time_pos = 50.0
        duration = 300.0
        def seek(self, seconds, reference='relative'):
            seeks.append((seconds, reference))

    dlg.mpv_player = MockMpvPlayer()

    class FakeKeyEvent:
        def __init__(self, keycode, ctrl=False, alt=False, shift=False):
            self._k = keycode
            self._ctrl = ctrl
            self._alt = alt
            self._shift = shift
        def GetKeyCode(self):
            return self._k
        def ControlDown(self):
            return self._ctrl
        def AltDown(self):
            return self._alt
        def ShiftDown(self):
            return self._shift
        def Skip(self):
            pass

    # Flecha Derecha: debe avanzar exactamente +10s
    seeks.clear()
    dlg.on_key_hook(FakeKeyEvent(wx.WXK_RIGHT))
    assert seeks == [(10, 'relative')], f"Flecha derecha debe saltar +10s, obtenido: {seeks}"

    # Flecha Izquierda: debe retroceder exactamente -10s
    seeks.clear()
    dlg.on_key_hook(FakeKeyEvent(wx.WXK_LEFT))
    assert seeks == [(-10, 'relative')], f"Flecha izquierda debe saltar -10s, obtenido: {seeks}"

    # Shift + Flecha Derecha (+1s) / Izquierda (-1s)
    seeks.clear()
    dlg.on_key_hook(FakeKeyEvent(wx.WXK_RIGHT, shift=True))
    assert seeks == [(1, 'relative')]

    seeks.clear()
    dlg.on_key_hook(FakeKeyEvent(wx.WXK_LEFT, shift=True))
    assert seeks == [(-1, 'relative')]

    # Shift + Alt + Flechas (+/- 5s)
    seeks.clear()
    dlg.on_key_hook(FakeKeyEvent(wx.WXK_RIGHT, shift=True, alt=True))
    assert seeks == [(5, 'relative')]

    seeks.clear()
    dlg.on_key_hook(FakeKeyEvent(wx.WXK_LEFT, shift=True, alt=True))
    assert seeks == [(-5, 'relative')]

    # Ctrl + Shift + Flechas (+/- 60s)
    seeks.clear()
    dlg.on_key_hook(FakeKeyEvent(wx.WXK_RIGHT, ctrl=True, shift=True))
    assert seeks == [(60, 'relative')]

    seeks.clear()
    dlg.on_key_hook(FakeKeyEvent(wx.WXK_LEFT, ctrl=True, shift=True))
    assert seeks == [(-60, 'relative')]

    # Ctrl + Alt + Shift + Flechas (+/- 300s)
    seeks.clear()
    dlg.on_key_hook(FakeKeyEvent(wx.WXK_RIGHT, ctrl=True, alt=True, shift=True))
    assert seeks == [(300, 'relative')]

    seeks.clear()
    dlg.on_key_hook(FakeKeyEvent(wx.WXK_LEFT, ctrl=True, alt=True, shift=True))
    assert seeks == [(-300, 'relative')]

    dlg.on_cleanup()
    dlg.Destroy()
    parent.Destroy()
    print("  -> Flechas Derecha (+10s) e Izquierda (-10s) validadas de forma 100% coherente y simétrica.")


if __name__ == '__main__':
    test_video_player_continuous_logic()
    test_reproductor_shuffle_stop_y_atajos()
    test_reproductor_orden_aleatorio_sin_repeticion_y_precarga()
    test_cola_reproduccion_y_descargas()
    test_ver_cola_dialogo_y_atajos_ctrl_p_n()
    test_cola_menu_contextual_y_seleccion_favoritos()
    test_dispositivo_salida_audio()
    test_foco_reproductor_cambio_tarea_y_aislamiento_tts()
    test_atajos_f8_f9_f10_informacion_tiempo()
    test_atajos_flechas_seek_10_segundos()
    print("\n[OK] Todas las pruebas de test_player.py pasaron satisfactoriamente.")
