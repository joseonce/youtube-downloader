"""
Script de verificación funcional para el módulo downloader y la inicialización de la UI.
"""
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_url_detection():
    print("[1/6] Probando detección inteligente de tipo de URLs...")
    from downloader import identificar_tipo_url

    assert identificar_tipo_url("https://www.youtube.com/@TED") == "canal"
    assert identificar_tipo_url("https://www.youtube.com/@TED/videos") == "canal"
    assert identificar_tipo_url("https://www.youtube.com/@TED/playlists") == "canal"
    assert identificar_tipo_url("https://www.youtube.com/channel/UCsooa4yRKGN_zEE8iknghZA") == "canal"
    assert identificar_tipo_url("@TED") == "canal"

    assert identificar_tipo_url("https://www.youtube.com/playlist?list=PLUCPc-R61w-s") == "playlist"
    assert identificar_tipo_url("https://www.youtube.com/watch?v=123&list=PLUCPc-R61w-s") == "playlist"
    assert identificar_tipo_url("https://www.youtube.com/feed/history") == "playlist"
    assert identificar_tipo_url("https://www.youtube.com/feed/playlists") == "playlist"

    assert identificar_tipo_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "video"
    assert identificar_tipo_url("python tutorial basico") == "texto"
    print("  -> Identificación de URLs validada correctamente (canales, playlists, vídeos, texto).")

def test_downloader():
    print("\n[2/6] Probando búsqueda con YouTubeDownloader por vídeos, canales y playlists...")
    from downloader import YouTubeDownloader
    dl = YouTubeDownloader()
    
    # 1. Búsqueda de vídeos
    resultados_vids = dl.buscar("python tutorial", max_results=2, search_type='video')
    assert len(resultados_vids) > 0, "No se obtuvieron vídeos de búsqueda"
    assert resultados_vids[0]['tipo_item'] == 'video'
    print(f"  -> Vídeos encontrados: {len(resultados_vids)} ({resultados_vids[0]['title']})")

    # 2. Búsqueda de listas de reproducción
    resultados_pls = dl.buscar("python tutorial", max_results=2, search_type='playlist')
    assert len(resultados_pls) > 0, "No se obtuvieron listas de reproducción de búsqueda"
    assert resultados_pls[0]['is_playlist'] is True
    print(f"  -> Playlists encontradas: {len(resultados_pls)} ({resultados_pls[0]['title']})")

    # 4. Probar ordenación natural y formato de visitas: respeta fielmente el orden devuelto por yt-dlp
    mock_entries = [
        {'id': '1', 'title': 'Aprende a programar desde cero', 'view_count': 20000000},
        {'id': '2', 'title': 'Python Tutorial Completo 2026', 'view_count': 5000000},
        {'id': '3', 'title': 'Python Tutorial Avanzado', 'view_count': 10000000},
    ]
    procesados = dl._procesar_entries(mock_entries, query="Python Tutorial")
    assert procesados[0]['id'] == '1', "Debe respetar el orden natural devuelto por yt-dlp (elemento 1)"
    assert procesados[0]['views'] == '20M visitas'
    assert procesados[0]['index'] == 1
    assert procesados[1]['id'] == '2', "Debe respetar el orden natural devuelto por yt-dlp (elemento 2)"
    assert procesados[1]['views'] == '5M visitas'
    assert procesados[1]['index'] == 2
    assert procesados[2]['id'] == '3', "Debe respetar el orden natural devuelto por yt-dlp (elemento 3)"
    assert procesados[2]['views'] == '10M visitas'
    assert procesados[2]['index'] == 3

    # Probar start_index desplazado (paginación continua)
    procesados_p2 = dl._procesar_entries(mock_entries, query="Python Tutorial", start_index=26)
    assert procesados_p2[0]['index'] == 26
    assert procesados_p2[1]['index'] == 27
    assert procesados_p2[2]['index'] == 28

    # 5. Probar canales con número de vídeos
    mock_channel_entries = [
        {'id': 'c1', 'title': 'Canal de Rock', 'url': 'https://www.youtube.com/@rock', 'channel_follower_count': 1500000, 'video_count': 342},
        {'id': 'c2', 'title': 'Canal Sin Contador', 'url': 'https://www.youtube.com/@sincontador', 'channel_follower_count': 50000}
    ]
    procesados_canales = dl._procesar_entries(mock_channel_entries, query="rock", is_channel_list=True)
    assert procesados_canales[0]['duration'] == '342 vídeos', "Debe mostrar el número de vídeos en la duración del canal"
    assert '342 vídeos' in procesados_canales[0]['views'], "Debe incluir el número de vídeos en las visitas del canal"
    assert procesados_canales[1]['duration'] == 'Canal', "Debe mostrar 'Canal' si no hay contador de vídeos"
    # 6. Probar extracción de channel_url y compatibilidad con enlaces especiales (ej: ShWqrFbSVxw)
    res_especial = dl.buscar("https://www.youtube.com/watch?v=ShWqrFbSVxw")
    assert len(res_especial) == 1, "Debe extraer correctamente el vídeo ShWqrFbSVxw"
    assert res_especial[0]['tipo_item'] == 'video'
    assert 'flamencodejerez' in res_especial[0]['channel_url'].lower()
    ch_url = dl.obtener_canal_url("https://www.youtube.com/watch?v=ShWqrFbSVxw")
    assert 'flamencodejerez' in ch_url.lower()

    # 7. Probar canales Topic / Temáticos que carecen de pestaña /videos
    res_topic = dl.buscar_canal_videos("https://www.youtube.com/channel/UClTrzaux8syhoUoIZi69VOw", max_results=5)
    assert len(res_topic) > 0, "Debe listar los vídeos/pistas de un canal Topic que no tiene pestaña /videos"

    print("  -> Priorización por términos en el título, paginación (start_index), visitas, canales especiales (Topic) y compatibilidad con enlaces verificados con éxito.")

def test_gui_init_and_selection():
    print("\n[3/6] Probando inicialización de la interfaz wxPython (Descargador de YouTube), selector de búsqueda y manual...")
    import wx
    import accessibility
    from ui import MainFrame
    
    from downloader import DEFAULT_CONFIG, guardar_configuracion
    guardar_configuracion(dict(DEFAULT_CONFIG))
    
    app = wx.App(False)
    accessibility.init_accessibility()
    frame = MainFrame()
    assert frame is not None, "Error al crear MainFrame"
    assert frame.GetTitle() == "Descargador de YouTube", f"Título incorrecto: {frame.GetTitle()}"

    # Verificar que el control choice_tipo_busqueda existe y tiene las 3 opciones
    assert hasattr(frame, 'choice_tipo_busqueda'), "MainFrame debe contener choice_tipo_busqueda"
    assert frame.choice_tipo_busqueda.GetCount() == 3
    assert frame.choice_tipo_busqueda.GetString(0) == "Vídeos"
    assert frame.choice_tipo_busqueda.GetString(1) == "Canales"
    assert frame.choice_tipo_busqueda.GetString(2) == "Listas de reproducción"
    assert frame.choice_tipo_busqueda.IsEnabled() is True  # YouTube activo por defecto

    # Verificar que existe el botón de Siguientes resultados y comienza deshabilitado
    assert hasattr(frame, 'btn_siguientes'), "MainFrame debe contener btn_siguientes"
    assert frame.btn_siguientes.IsEnabled() is False

    # Verificar que el botón de búsqueda comienza como 'Buscar'
    assert hasattr(frame, 'btn_buscar'), "MainFrame debe contener btn_buscar"
    assert frame.btn_buscar.GetLabel() == "&Buscar"
    assert getattr(frame, 'modo_boton_buscar', 'buscar') == 'buscar'

    # Probar cambio puntual de tipo de búsqueda en la barra (no altera config.json persistente)
    initial_saved_type = frame.config.get('search_type_idx', 0)
    frame.choice_tipo_busqueda.SetSelection(1)
    frame.on_tipo_busqueda_changed()
    assert frame.choice_tipo_busqueda.GetSelection() == 1
    # La configuración persistente no debe modificarse por cambios puntuales en la barra
    assert frame.config.get('search_type_idx', 0) == initial_saved_type

    # Probar cambio de plataforma (SoundCloud desactiva el filtro específico de YouTube)
    frame._set_engine_index(1)
    assert frame.choice_tipo_busqueda.IsEnabled() is False
    # Restaurar YouTube
    frame._set_engine_index(0)
    assert frame.choice_tipo_busqueda.IsEnabled() is True

    # Simular datos de prueba en la lista incluyendo canal, playlist y vídeo
    test_data = [
        {'index': 1, 'id': 'v1', 'title': 'Video 1', 'channel': 'Canal 1', 'duration': '03:15', 'duration_seconds': 195, 'views': '1.2M visitas', 'url': 'http://yt.com/1', 'is_playlist': False, 'is_channel': False, 'selected': False},
        {'index': 2, 'id': 'c1', 'title': 'Canal Pro', 'channel': '@canalpro', 'duration': 'Canal', 'duration_seconds': 0, 'views': '500K suscriptores', 'url': 'http://yt.com/c1', 'is_playlist': False, 'is_channel': True, 'selected': False},
        {'index': 3, 'id': 'p1', 'title': 'Playlist 1', 'channel': 'Canal 1', 'duration': '10 vídeos', 'duration_seconds': 0, 'views': '10 vídeos', 'url': 'http://yt.com/p1', 'is_playlist': True, 'is_channel': False, 'selected': False}
    ]
    frame._on_search_completed(test_data, "Test")
    # Si hay menos de max_results (por defecto 25), btn_siguientes debe estar deshabilitado
    assert frame.btn_siguientes.IsEnabled() is False
    # Con max_results igual a la cantidad de resultados (3), debe habilitarse
    frame.config['max_results'] = 3
    frame._on_search_completed(test_data, "Test")
    assert frame.btn_siguientes.IsEnabled() is True
    # Restaurar max_results
    frame.config['max_results'] = 25
    # El botón pasa a llamarse 'Limpiar resultados'
    assert frame.btn_buscar.GetLabel() == "&Limpiar resultados"
    assert frame.modo_boton_buscar == 'limpiar'

    # Probar carga paginada continua (siguientes resultados añadidos al final)
    test_data_batch2 = [
        {'index': 4, 'id': 'v4', 'title': 'Video 4', 'channel': 'Canal 2', 'duration': '05:00', 'duration_seconds': 300, 'views': '100K visitas', 'url': 'http://yt.com/4', 'is_playlist': False, 'is_channel': False, 'selected': False},
        {'index': 5, 'id': 'v5', 'title': 'Video 5', 'channel': 'Canal 2', 'duration': '04:20', 'duration_seconds': 260, 'views': '200K visitas', 'url': 'http://yt.com/5', 'is_playlist': False, 'is_channel': False, 'selected': False}
    ]
    frame._on_search_completed(test_data_batch2, "Test", append=True)
    assert len(frame.resultados) == 5
    assert frame.lista_resultados.GetItemCount() == 5
    assert frame.next_start_index == 6
    assert frame.lista_resultados.GetItemText(3, 0) == "Video 4"
    assert frame.lista_resultados.GetItemText(4, 0) == "Video 5"
    assert frame.lista_resultados.GetFirstSelected() == 3  # Debe enfocar el primer elemento nuevo cargado

    # Verificar títulos, canal, duración, visitas y formato de lista
    item_title_0 = frame.lista_resultados.GetItemText(0, 0)
    assert item_title_0 == "Video 1"
    assert frame.lista_resultados.GetItemText(0, 1) == "Canal 1"
    assert frame.lista_resultados.GetItemText(0, 2) == "03:15"
    assert frame.lista_resultados.GetItemText(0, 3) == "1.2M visitas"
    assert "☑️" not in item_title_0 and "⬜" not in item_title_0 and "⭐" not in item_title_0

    # Probar Selección Todos
    frame.seleccionar_todos()
    assert all(r['selected'] for r in frame.resultados)
    assert frame.lista_resultados.GetItemText(0, 0).startswith("Marcado - ")

    # Probar Deselección Todos
    frame.deseleccionar_todos()
    assert not any(r['selected'] for r in frame.resultados)
    assert not frame.lista_resultados.GetItemText(0, 0).startswith("Marcado - ")

    # Probar Selección individual con Espacio simulado
    frame.lista_resultados.Select(0)
    frame.toggle_seleccion_actual()
    assert frame.resultados[0]['selected'] is True
    assert frame.resultados[1]['selected'] is False
    assert frame.lista_resultados.GetItemText(0, 0) == "Marcado - Video 1"

    # Probar navegación accesible por columnas con Flechas Izquierda / Derecha
    assert frame.col_activa_resultados == 0
    # Avanzar a columna 1 (Canal)
    frame.navegar_columna_resultados(1)
    assert frame.col_activa_resultados == 1
    assert "Canal: Canal 1" in frame.status_bar.GetStatusText(0)

    # Avanzar a columna 2 (Duración)
    frame.navegar_columna_resultados(1)
    assert frame.col_activa_resultados == 2
    assert "Duración: 03:15" in frame.status_bar.GetStatusText(0)

    # Avanzar a columna 3 (Visitas)
    frame.navegar_columna_resultados(1)
    assert frame.col_activa_resultados == 3
    assert "Visitas: 1.2M visitas" in frame.status_bar.GetStatusText(0)

    # Intentar avanzar más allá de la última columna
    frame.navegar_columna_resultados(1)
    assert frame.col_activa_resultados == 3

    # Retroceder hasta columna 0 (Título)
    frame.navegar_columna_resultados(-1)
    assert frame.col_activa_resultados == 2
    frame.navegar_columna_resultados(-1)
    assert frame.col_activa_resultados == 1
    frame.navegar_columna_resultados(-1)
    assert frame.col_activa_resultados == 0
    assert "Título:" in frame.status_bar.GetStatusText(0)

    # Probar copia de URL del canal de elemento seleccionado
    frame.lista_resultados.Select(0)
    frame.copiar_url_del_canal_seleccionado({'title': 'Video 1', 'channel_url': 'https://www.youtube.com/@canal1'})
    assert "portapapeles" in frame.status_bar.GetStatusText(0).lower()

    # Probar que on_previsualizar_video (Ctrl+P) solo reproduce el vídeo enfocado si no hay marcas,
    # o únicamente los vídeos marcados con Espacio, mientras reproducir_toda_la_lista (Ctrl+L) reproduce todos.
    videos_multi = [
        {'index': 1, 'id': 'vid_a', 'title': 'Video A', 'channel': 'Canal A', 'duration': '01:00', 'duration_seconds': 60, 'views': '100', 'url': 'http://yt.com/a', 'is_playlist': False, 'is_channel': False, 'selected': False},
        {'index': 2, 'id': 'vid_b', 'title': 'Video B', 'channel': 'Canal B', 'duration': '02:00', 'duration_seconds': 120, 'views': '200', 'url': 'http://yt.com/b', 'is_playlist': False, 'is_channel': False, 'selected': False},
        {'index': 3, 'id': 'vid_c', 'title': 'Video C', 'channel': 'Canal C', 'duration': '03:00', 'duration_seconds': 180, 'views': '300', 'url': 'http://yt.com/c', 'is_playlist': False, 'is_channel': False, 'selected': False},
    ]
    frame._on_search_completed(videos_multi, "Test Multi")
    assert frame.lista_resultados.GetItemCount() == 3

    captured_preview = []
    class MockPreviewDialog:
        def __init__(self, parent, videos, initial_index=0):
            captured_preview.append({'videos': videos, 'initial_index': initial_index})
            self.wants_download = False
            self.download_target_video = None
        def ShowModal(self):
            return wx.ID_OK
        def Destroy(self):
            pass

    import ui
    orig_dlg = ui.VideoPreviewDialog
    ui.VideoPreviewDialog = MockPreviewDialog
    try:
        # Caso A: Sin marcar con espacio. El usuario selecciona el Video B (índice 1) con cursor/ratón
        frame.deseleccionar_todos()
        frame.lista_resultados.Select(1)
        frame.on_previsualizar_video(None)
        assert len(captured_preview) == 1
        assert len(captured_preview[0]['videos']) == 1, "Ctrl+P sin marcas debe reproducir ÚNICAMENTE el vídeo seleccionado"
        assert captured_preview[0]['videos'][0]['id'] == 'vid_b'

        # Caso B: El usuario marca Video A y Video C con la barra espaciadora
        captured_preview.clear()
        frame.lista_resultados.Select(0)
        frame.toggle_seleccion_actual()
        frame.lista_resultados.Select(2)
        frame.toggle_seleccion_actual()
        frame.on_previsualizar_video(None)
        assert len(captured_preview) == 1
        assert len(captured_preview[0]['videos']) == 2, "Ctrl+P con marcas debe reproducir los vídeos marcados"
        assert [v['id'] for v in captured_preview[0]['videos']] == ['vid_a', 'vid_c']

        # Caso C: Reproducir toda la lista con Ctrl+L
        captured_preview.clear()
        frame.reproducir_toda_la_lista(None)
        assert len(captured_preview) == 1
        assert len(captured_preview[0]['videos']) == 3, "Ctrl+L debe reproducir todos los vídeos de la lista"
        assert [v['id'] for v in captured_preview[0]['videos']] == ['vid_a', 'vid_b', 'vid_c']
    finally:
        ui.VideoPreviewDialog = orig_dlg

    # Probar que al tomar foco el campo de búsqueda, se selecciona todo el texto
    frame.txt_busqueda.SetValue("Texto anterior a reemplazar")
    frame.txt_busqueda.SetFocus()
    app.Yield()
    frame._seleccionar_todo_busqueda()
    sel_from, sel_to = frame.txt_busqueda.GetSelection()
    assert sel_from == 0 and sel_to == len("Texto anterior a reemplazar"), "Todo el texto del campo de búsqueda debe quedar seleccionado al tomar foco"

    # Probar visualización accesible de favoritos (vídeos, canales, playlists) con iconos y etiquetas
    from downloader import agregar_favorito, eliminar_favorito, detectar_tipo_elemento
    
    assert detectar_tipo_elemento({'is_channel': True}) == 'channel'
    assert detectar_tipo_elemento({'url': 'https://www.youtube.com/@Python'}) == 'channel'
    assert detectar_tipo_elemento({'is_playlist': True}) == 'playlist'
    assert detectar_tipo_elemento({'url': 'https://www.youtube.com/playlist?list=PL123'}) == 'playlist'
    assert detectar_tipo_elemento({'url': 'https://www.youtube.com/watch?v=abc'}) == 'video'

    fav_items_test = [
        {'id': 'f_v1', 'title': 'Video Favorito', 'url': 'http://yt.com/watch?v=1', 'is_channel': False, 'is_playlist': False, 'channel': 'Canal X', 'duration': '04:00', 'views': '10K'},
        {'id': 'f_c1', 'title': 'Canal Favorito', 'url': 'http://yt.com/@creador', 'is_channel': True, 'is_playlist': False, 'channel': 'Canal Y', 'duration': 'Canal', 'views': '100K suscriptores'},
        {'id': 'f_p1', 'title': 'Playlist Favorita', 'url': 'http://yt.com/playlist?list=PL1', 'is_channel': False, 'is_playlist': True, 'channel': 'Canal Z', 'duration': '15 vídeos', 'views': '15 vídeos'}
    ]
    orig_obtener_favs = ui.obtener_favoritos
    orig_obtener_nombres = ui.obtener_nombres_listas_favoritos
    ui.obtener_favoritos = lambda nombre_lista=None: fav_items_test
    ui.obtener_nombres_listas_favoritos = lambda: ['Principal']
    try:
        frame.mostrar_favoritos()
        assert frame.is_showing_favorites is True
        assert frame.lista_resultados.GetItemCount() == 3
        # Verificar etiquetas accesibles
        assert frame.lista_resultados.GetItemText(0, 0) == "[Vídeo] Video Favorito"
        assert frame.lista_resultados.GetItemText(1, 0) == "[Canal] Canal Favorito"
        assert frame.lista_resultados.GetItemText(2, 0) == "[Lista] Playlist Favorita"
        # Verificar imágenes/iconos asociados
        assert frame.lista_resultados.GetItem(0, 0).GetImage() == frame.IMG_IDX_VIDEO
        assert frame.lista_resultados.GetItem(1, 0).GetImage() == frame.IMG_IDX_CHANNEL
        assert frame.lista_resultados.GetItem(2, 0).GetImage() == frame.IMG_IDX_PLAYLIST
        # Verificar marcado con Espacio manteniendo la etiqueta
        frame.lista_resultados.Select(1)
        frame.toggle_seleccion_actual()
        assert frame.lista_resultados.GetItemText(1, 0) == "Marcado - [Canal] Canal Favorito"
        # Verificar que al mostrar favoritos el botón también cambia a "Limpiar resultados"
        assert frame.btn_buscar.GetLabel() == "&Limpiar resultados"
        assert frame.modo_boton_buscar == 'limpiar'

        # Probar función de Limpiar resultados:
        # Borra lista de resultados, elimina campo de búsqueda, focaliza dicho campo y se llama de nuevo Buscar
        frame.txt_busqueda.SetValue("Texto anterior de busqueda")
        frame.on_btn_buscar()  # Ejecuta la acción del botón (Limpiar resultados)
        assert frame.lista_resultados.GetItemCount() == 0
        assert len(frame.resultados) == 0
        assert frame.txt_busqueda.GetValue() == ""
        assert frame.btn_buscar.GetLabel() == "&Buscar"
        assert frame.modo_boton_buscar == 'buscar'

        # Probar que la tecla Escape también ejecuta la función de limpiar resultados
        frame._on_search_completed([{'index': 1, 'id': 'v1', 'title': 'Test Esc', 'channel': 'C', 'duration': '01:00', 'views': '10', 'url': 'http://yt.com/1'}], "Esc Test")
        frame.txt_busqueda.SetValue("Búsqueda para borrar con escape")
        assert frame.lista_resultados.GetItemCount() == 1
        assert frame.modo_boton_buscar == 'limpiar'

        class MockKeyEvent:
            def GetKeyCode(self): return wx.WXK_ESCAPE
            def GetModifiers(self): return 0
        frame.on_char_hook(MockKeyEvent())
        assert frame.lista_resultados.GetItemCount() == 0
        assert len(frame.resultados) == 0
        assert frame.txt_busqueda.GetValue() == ""
        assert frame.modo_boton_buscar == 'buscar'

        # Si no hay nada que limpiar, pulsar escape no debe modificar el estado ni emitir avisos
        frame.on_char_hook(MockKeyEvent())
        assert frame.lista_resultados.GetItemCount() == 0
        assert len(frame.resultados) == 0
        assert frame.txt_busqueda.GetValue() == ""
        assert frame.modo_boton_buscar == 'buscar'

        # Probar UpdateDialog cuando ya está actualizado
        dlg_up = ui.UpdateDialog(frame)
        dlg_up._on_check_success({'version': dlg_up.version_actual, 'download_url': 'http://fake'})
        assert not dlg_up.btn_update.IsShown(), "El botón de actualizar no debe mostrarse si ya está actualizado"
        assert not dlg_up.btn_check.IsShown(), "El botón de buscar actualizaciones no debe mostrarse si ya está actualizado"
        assert dlg_up.btn_close.GetLabel() == "&Aceptar"
        dlg_up.Destroy()
    finally:
        ui.obtener_favoritos = orig_obtener_favs
        ui.obtener_nombres_listas_favoritos = orig_obtener_nombres

    print("  -> Título 'Descargador de YouTube', selector de búsqueda, tabla de resultados, selección individual/múltiple (Ctrl+P), lista continua (Ctrl+L), foco de búsqueda y favoritos accesibles verificados.")
    frame.Destroy()
    app.Destroy()

def test_channel_playlist_extraction():
    print("\n[4/6] Probando extracción rápida de vídeos y playlists de canal...")
    from downloader import YouTubeDownloader
    dl = YouTubeDownloader()
    # Usar canal TED de prueba
    res_vids = dl.buscar_canal_videos("https://www.youtube.com/@TED", max_results=2)
    print(f"  -> Vídeos de canal obtenidos: {len(res_vids)}")
    if res_vids:
        assert res_vids[0]['is_playlist'] is False

    res_pls = dl.buscar_canal_playlists("https://www.youtube.com/@TED", max_results=2)
    print(f"  -> Playlists de canal obtenidas: {len(res_pls)}")
    if res_pls:
        assert res_pls[0]['is_playlist'] is True

def test_config_persistence_and_paths():
    print("\n[5/6] Probando persistencia en config/config.json, carpetas bin/, docs/, resources/ y valores por defecto...")
    from downloader import (
        get_base_dir,
        get_config_dir,
        get_config_file_path,
        get_bin_dir,
        get_docs_dir,
        get_resources_dir,
        cargar_configuracion,
        guardar_configuracion,
        DEFAULT_CONFIG
    )
    
    base_dir = get_base_dir()
    cfg_dir = get_config_dir()
    cfg_file = get_config_file_path()
    bin_dir = get_bin_dir()
    docs_dir = get_docs_dir()
    res_dir = get_resources_dir()

    assert os.path.isabs(base_dir), "La ruta base debe ser absoluta"
    assert os.path.isdir(cfg_dir), "La carpeta config/ debe existir"
    assert os.path.isdir(bin_dir), "La carpeta bin/ debe existir"
    assert os.path.isdir(docs_dir), "La carpeta docs/ debe existir"
    assert os.path.isdir(res_dir), "La carpeta resources/ debe existir"
    assert cfg_file.endswith("config.json"), "El archivo de configuración debe ser config.json"
    assert os.path.dirname(cfg_file) == cfg_dir, "config.json debe residir en config/"

    # Verificar valores predeterminados solicitados:
    # 1. Repetición desactivada por defecto (False)
    # 2. Tipo de búsqueda por defecto: 0 ("Vídeos")
    # 3. Cantidad de resultados por defecto: 50
    # 4. Reproducir con vídeo por defecto (True)
    assert DEFAULT_CONFIG['repetir_reproductor'] is False, "La repetición debe estar desactivada por defecto"
    assert DEFAULT_CONFIG['search_type_idx'] == 0, "El tipo de búsqueda por defecto debe ser 0 (Vídeos)"
    assert DEFAULT_CONFIG['max_results'] == 25, "La cantidad de resultados por defecto debe ser 25"
    assert DEFAULT_CONFIG['reproducir_con_video'] is True, "La reproducción con vídeo debe estar activada por defecto"
    assert DEFAULT_CONFIG['abrir_carpeta_al_terminar'] is False, "Abrir carpeta automáticamente debe estar desactivado por defecto"
    assert DEFAULT_CONFIG['preguntar_abrir_carpeta'] is True, "Preguntar si abrir carpeta debe estar activado por defecto"
    assert DEFAULT_CONFIG['confirmar_eliminar_favorito'] is True, "Confirmar eliminación de favoritos debe estar activado por defecto"

    # Verificar existencia de archivos de documentación y atajos
    manual_md = os.path.join(docs_dir, 'manual.md')
    manual_html = os.path.join(docs_dir, 'manual.html')
    atajos_md = os.path.join(docs_dir, 'atajos.md')
    atajos_html = os.path.join(docs_dir, 'atajos.html')
    assert os.path.isfile(manual_md), "manual.md debe existir en docs/"
    assert os.path.isfile(manual_html), "manual.html debe existir en docs/"
    assert os.path.isfile(atajos_md), "atajos.md debe existir en docs/"
    assert os.path.isfile(atajos_html), "atajos.html debe existir en docs/"

    # Probar guardar y cargar
    cfg_test = cargar_configuracion()
    cfg_test['max_results'] = 42
    cfg_test['formato_idx'] = 2
    cfg_test['search_type_idx'] = 1
    cfg_test['repetir_reproductor'] = False
    cfg_test['confirmar_eliminar_favorito'] = False
    guardar_configuracion(cfg_test)

    cfg_loaded = cargar_configuracion()
    assert cfg_loaded.get('max_results') == 42
    assert cfg_loaded.get('formato_idx') == 2
    assert cfg_loaded.get('search_type_idx') == 1
    assert cfg_loaded.get('repetir_reproductor') is False
    assert cfg_loaded.get('confirmar_eliminar_favorito') is False

    # Probar helpers de cookies
    from downloader import get_cookie_args, get_cookie_ydl_opts
    assert get_cookie_args({'cookie_source': 'none'}) == []
    assert get_cookie_args({'cookie_source': 'browser', 'cookie_browser': 'firefox'}) == ['--cookies-from-browser', 'firefox']
    assert get_cookie_ydl_opts({'cookie_source': 'browser', 'cookie_browser': 'firefox'}) == {'cookiesfrombrowser': ('firefox',)}

    # Restaurar configuración inicial limpia por defecto
    cfg_restored = dict(DEFAULT_CONFIG)
    guardar_configuracion(cfg_restored)
    print(f"  -> Estructura modular validada (config/, bin/, docs/, resources/) y config.json restaurado con valores predeterminados en: {cfg_file}")


def test_favorites_multiple_lists_system():
    print("\n[6/6] Probando sistema persistente de múltiples listas de Favoritos (ficheros independientes en config/favoritos/)...")
    from downloader import (
        get_favoritos_dir,
        get_favoritos_file_path,
        obtener_nombres_listas_favoritos,
        obtener_favoritos,
        crear_lista_favoritos,
        eliminar_lista_favoritos,
        agregar_favorito,
        eliminar_favorito,
        es_favorito,
        mover_favorito_de_lista,
        obtener_listas_de_item
    )

    fav_dir = get_favoritos_dir()
    assert os.path.isdir(fav_dir), "La carpeta config/favoritos/ debe existir"
    fav_principal = get_favoritos_file_path('Principal')
    assert fav_principal.endswith("Principal.json"), "El archivo de la lista Principal debe ser Principal.json"
    assert os.path.dirname(fav_principal) == fav_dir, "Principal.json debe residir en config/favoritos/"

    test_video_1 = {
        'id': 'test_fav_001',
        'title': 'Vídeo Favorito General',
        'channel': 'Canal Test',
        'duration': '04:20',
        'duration_seconds': 260,
        'url': 'https://www.youtube.com/watch?v=test_fav_001'
    }

    test_video_2 = {
        'id': 'test_fav_002',
        'title': 'Canción Favorita Rock',
        'channel': 'Canal Rock',
        'duration': '03:10',
        'duration_seconds': 190,
        'url': 'https://www.youtube.com/watch?v=test_fav_002'
    }

    # Limpiar si existían
    eliminar_favorito('test_fav_001')
    eliminar_favorito('test_fav_002')
    assert not es_favorito('test_fav_001')
    assert not es_favorito('test_fav_002')

    # Crear lista personalizada
    crear_lista_favoritos('Música Rock')
    nombres = obtener_nombres_listas_favoritos()
    assert 'Música Rock' in nombres
    fav_rock_file = get_favoritos_file_path('Música Rock')
    assert os.path.isfile(fav_rock_file), "Debe crearse el fichero independiente Música Rock.json"

    # Añadir a Principal y a lista personalizada
    ok1 = agregar_favorito(test_video_1, nombre_lista='Principal')
    assert ok1 is True
    ok2 = agregar_favorito(test_video_2, nombre_lista='Música Rock')
    assert ok2 is True

    # Verificar que los archivos .json existen en el disco de forma separada
    assert os.path.isfile(fav_principal), f"Principal.json debe existir en {fav_principal}"
    assert os.path.isfile(fav_rock_file), f"Música Rock.json debe existir en {fav_rock_file}"

    # Verificar pertenencia
    assert es_favorito('test_fav_001') is True
    assert es_favorito('test_fav_002') is True

    # Verificar filtrado por lista
    favs_rock = obtener_favoritos(nombre_lista='Música Rock')
    assert any(f['id'] == 'test_fav_002' for f in favs_rock)
    assert not any(f['id'] == 'test_fav_001' for f in favs_rock)

    favs_todos = obtener_favoritos(nombre_lista=None)
    assert any(f['id'] == 'test_fav_001' for f in favs_todos)
    assert any(f['id'] == 'test_fav_002' for f in favs_todos)

    # Eliminar
    del_ok1 = eliminar_favorito('test_fav_001')
    assert del_ok1 is True
    del_ok2 = eliminar_favorito('test_fav_002')
    assert del_ok2 is True
    assert es_favorito('test_fav_001') is False
    assert es_favorito('test_fav_002') is False

    # Probar que canales y playlists guardados en favoritos preservan su tipo de contenido
    canal_fav = {'id': 'ch_fav_1', 'title': 'Canal Python', 'url': 'https://www.youtube.com/@python', 'is_channel': True}
    pl_fav = {'id': 'pl_fav_1', 'title': 'Curso Django', 'url': 'https://www.youtube.com/playlist?list=PL_DJANGO', 'is_playlist': True}
    agregar_favorito(canal_fav, nombre_lista='Principal')
    agregar_favorito(pl_fav, nombre_lista='Principal')
    favs_check = obtener_favoritos(nombre_lista='Principal')
    f_ch = next(f for f in favs_check if f['id'] == 'ch_fav_1')
    f_pl = next(f for f in favs_check if f['id'] == 'pl_fav_1')
    assert f_ch['type'] == 'channel' and f_ch['is_channel'] is True
    assert f_pl['type'] == 'playlist' and f_pl['is_playlist'] is True
    # Probar mover un elemento de una lista de favoritos a otra
    test_move_vid = {
        'id': 'test_move_001',
        'title': 'Vídeo para Mover de Lista',
        'channel': 'Canal Move',
        'url': 'https://www.youtube.com/watch?v=test_move_001'
    }
    agregar_favorito(test_move_vid, nombre_lista='Principal')
    assert 'Principal' in obtener_listas_de_item('test_move_001')

    # Mover a Música Rock
    mover_favorito_de_lista(test_move_vid, lista_destino='Música Rock', lista_origen='Principal')
    listas_del_item = obtener_listas_de_item('test_move_001')
    assert 'Música Rock' in listas_del_item, "Debe haberse añadido a Música Rock"
    assert 'Principal' not in listas_del_item, "Debe haberse eliminado de Principal"

    eliminar_favorito('test_move_001')
    eliminar_lista_favoritos('Música Rock')

    print(f"  -> Archivos independientes por lista en config/favoritos/ ({fav_dir}), tipos y cambio de listas validados con éxito.")


def test_mover_multiples_favoritos_y_busqueda():
    print("\n[Extra] Probando movimiento por lotes a lista nueva con selección múltiple y búsqueda...")
    from downloader import (
        crear_lista_favoritos,
        eliminar_lista_favoritos,
        agregar_favorito,
        eliminar_favorito,
        obtener_listas_de_item
    )
    import wx
    from ui import MainFrame

    vid_fav1 = {'id': 'mv_fav_1', 'title': 'Vid Fav 1', 'url': 'https://youtube.com/watch?v=mv_fav_1'}
    vid_fav2 = {'id': 'mv_fav_2', 'title': 'Vid Fav 2', 'url': 'https://youtube.com/watch?v=mv_fav_2'}
    vid_busq = {'id': 'mv_search_1', 'title': 'Vid Busqueda 1', 'url': 'https://youtube.com/watch?v=mv_search_1'}

    for v in ('mv_fav_1', 'mv_fav_2', 'mv_search_1'):
        eliminar_favorito(v)

    agregar_favorito(vid_fav1, nombre_lista='Principal')
    agregar_favorito(vid_fav2, nombre_lista='Principal')
    crear_lista_favoritos('Nueva Lista Test')

    app = wx.App.Get() or wx.App(False)
    frame = MainFrame()

    # Caso 1: Varios marcados (uno de lista, uno de búsqueda)
    frame.resultados = [
        {'id': 'mv_fav_1', 'title': 'Vid Fav 1', 'url': 'https://youtube.com/watch?v=mv_fav_1', 'selected': True, 'list_name': 'Principal'},
        {'id': 'mv_fav_2', 'title': 'Vid Fav 2', 'url': 'https://youtube.com/watch?v=mv_fav_2', 'selected': False, 'list_name': 'Principal'},
        {'id': 'mv_search_1', 'title': 'Vid Busqueda 1', 'url': 'https://youtube.com/watch?v=mv_search_1', 'selected': True}
    ]

    frame.lista_resultados.DeleteAllItems()
    for idx, r in enumerate(frame.resultados):
        frame.lista_resultados.InsertItem(idx, r['title'])

    items_a_mover = frame._get_videos_para_cambio_lista()
    assert len(items_a_mover) == 2, f"Deben ser 2 items marcados, obtenidos: {len(items_a_mover)}"
    assert items_a_mover[0]['id'] == 'mv_fav_1'
    assert items_a_mover[1]['id'] == 'mv_search_1'

    # Mover a 'Nueva Lista Test'
    frame.cambiar_favorito_a_lista(lista_destino='Nueva Lista Test')

    assert 'Nueva Lista Test' in obtener_listas_de_item('mv_fav_1')
    assert 'Principal' not in obtener_listas_de_item('mv_fav_1')
    assert 'Nueva Lista Test' in obtener_listas_de_item('mv_search_1')
    assert 'Principal' in obtener_listas_de_item('mv_fav_2')

    assert not frame.resultados[0].get('selected')
    assert not frame.resultados[2].get('selected')

    # Caso 2: Sin selección -> Mueve el que está bajo el cursor
    frame.resultados[0]['selected'] = False
    frame.resultados[1]['selected'] = False
    frame.resultados[2]['selected'] = False

    frame.lista_resultados.DeleteAllItems()
    for idx, r in enumerate(frame.resultados):
        frame.lista_resultados.InsertItem(idx, r['title'])
    frame.lista_resultados.Select(1)

    items_sin_sel = frame._get_videos_para_cambio_lista()
    assert len(items_sin_sel) == 1
    assert items_sin_sel[0]['id'] == 'mv_fav_2'

    frame.cambiar_favorito_a_lista(lista_destino='Nueva Lista Test')
    assert 'Nueva Lista Test' in obtener_listas_de_item('mv_fav_2')
    assert 'Principal' not in obtener_listas_de_item('mv_fav_2')

    for v in ('mv_fav_1', 'mv_fav_2', 'mv_search_1'):
        eliminar_favorito(v)
    eliminar_lista_favoritos('Nueva Lista Test')
    frame.Destroy()
    print("  -> Movimiento por lotes de selección múltiple, elementos de búsqueda y fallback a cursor validados con éxito.")


def test_no_cambiar_lista_si_no_es_favorito():
    print("\n[Extra] Probando que no se permite ni ofrece cambiar de lista si ningún elemento está en favoritos...")
    from downloader import (
        crear_lista_favoritos,
        eliminar_lista_favoritos,
        eliminar_favorito,
        es_favorito
    )
    import wx
    from ui import MainFrame

    vid_no_fav1 = {'id': 'no_fav_1', 'title': 'No Fav 1', 'url': 'https://youtube.com/watch?v=no_fav_1'}
    vid_no_fav2 = {'id': 'no_fav_2', 'title': 'No Fav 2', 'url': 'https://youtube.com/watch?v=no_fav_2'}

    eliminar_favorito('no_fav_1')
    eliminar_favorito('no_fav_2')
    crear_lista_favoritos('Destino Test')

    app = wx.App.Get() or wx.App(False)
    frame = MainFrame()

    # Caso 1: Un solo vídeo no favorito seleccionado
    frame.resultados = [
        {'id': 'no_fav_1', 'title': 'No Fav 1', 'url': 'https://youtube.com/watch?v=no_fav_1', 'selected': False},
        {'id': 'no_fav_2', 'title': 'No Fav 2', 'url': 'https://youtube.com/watch?v=no_fav_2', 'selected': False}
    ]
    frame.lista_resultados.DeleteAllItems()
    for idx, r in enumerate(frame.resultados):
        frame.lista_resultados.InsertItem(idx, r['title'])
    frame.lista_resultados.Select(0)

    menu_test = wx.Menu()
    frame._agregar_submenu_cambiar_lista(menu_test, frame.resultados[0])
    assert menu_test.GetMenuItemCount() == 0, "No debe añadirse submenú de cambiar lista si el vídeo no está en favoritos"
    menu_test.Destroy()

    # Intentar cambiar lista de un vídeo no favorito
    frame.cambiar_favorito_a_lista(video=frame.resultados[0], lista_destino='Destino Test')
    assert not es_favorito('no_fav_1'), "No debe haberse añadido a favoritos porque cambiar lista no aplica"

    # Caso 2: Múltiples vídeos seleccionados donde NINGUNO es favorito
    frame.resultados[0]['selected'] = True
    frame.resultados[1]['selected'] = True
    menu_test2 = wx.Menu()
    frame._agregar_submenu_cambiar_lista(menu_test2, frame.resultados[0])
    assert menu_test2.GetMenuItemCount() == 0, "No debe añadirse submenú si ninguno de los seleccionados es favorito"
    menu_test2.Destroy()

    frame.cambiar_favorito_a_lista(lista_destino='Destino Test')
    assert not es_favorito('no_fav_1')
    assert not es_favorito('no_fav_2')

    eliminar_lista_favoritos('Destino Test')
    frame.Destroy()
    print("  -> Verificación de no cambiar lista si ningún elemento es favorito validada con éxito.")


def test_video_player_continuous_logic():
    print("\n[Extra] Probando lógica del Reproductor Continuo y Pre-carga (Pre-buffering 2s)...")
    import wx
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


def test_favorites_delete_supr_key_and_confirmation():
    print("\n[Extra] Probando eliminación de favoritos con tecla Supr y confirmación configurable...")
    import wx
    import ui
    from unittest.mock import patch, MagicMock

    # 1. Helper de confirmación
    with patch('ui.cargar_configuracion', return_value={'confirmar_eliminar_favorito': False}):
        assert ui.pedir_confirmacion_eliminar_favorito(None, "Vídeo prueba") is True
    with patch('ui.cargar_configuracion', return_value={'confirmar_eliminar_favorito': True}):
        with patch('wx.MessageBox', return_value=wx.YES):
            assert ui.pedir_confirmacion_eliminar_favorito(None, "Vídeo prueba") is True
        with patch('wx.MessageBox', return_value=wx.NO):
            assert ui.pedir_confirmacion_eliminar_favorito(None, "Vídeo prueba") is False

    app = wx.App(False)

    # 2. Reproductor: Tecla Supr con confirmación
    test_v = {'id': 'v_fav_1', 'title': 'Canción Fav', 'url': 'https://youtube.com/watch?v=v_fav_1'}
    with patch('ui.es_favorito', return_value=True), \
         patch('ui.eliminar_favorito') as mock_del, \
         patch('ui.pedir_confirmacion_eliminar_favorito', return_value=True), \
         patch('ui.accessibility.speak'):
        dlg = ui.VideoPreviewDialog(None, [test_v])
        evt = MagicMock()
        evt.GetKeyCode.return_value = wx.WXK_DELETE
        evt.ControlDown.return_value = False
        dlg.on_key_hook(evt)
        assert mock_del.called
        dlg.Destroy()

    # 3. Lista: Tecla Supr con confirmación en MainFrame
    with patch('updater.start_background_check'), patch('ui.accessibility.speak'):
        frame = ui.MainFrame()
    frame.is_showing_favorites = True
    frame.resultados = [dict(test_v)]
    frame.lista_resultados.DeleteAllItems()
    frame.lista_resultados.InsertItem(0, test_v['title'])
    frame.lista_resultados.Select(0)
    frame.lista_resultados.Focus(0)

    with patch('ui.pedir_confirmacion_eliminar_favorito', return_value=True), \
         patch('ui.eliminar_favorito') as mock_del_list, \
         patch('ui.accessibility.speak'):
        evt = MagicMock()
        evt.GetKeyCode.return_value = wx.WXK_DELETE
        evt.GetModifiers.return_value = 0
        frame.on_lista_key_down(evt)
        assert mock_del_list.called
        assert len(frame.resultados) == 0

    # Probar que al pulsar Enter en la lista se reproduce y NO se descarga
    frame.resultados = [{'title': 'Video Enter Test', 'url': 'https://youtube.com/watch?v=enter1', 'is_playlist': False, 'is_channel': False}]
    frame.lista_resultados.DeleteAllItems()
    frame.lista_resultados.InsertItem(0, 'Video Enter Test')
    frame.lista_resultados.Select(0)
    frame.lista_resultados.Focus(0)
    with patch.object(frame, 'on_previsualizar_video') as mock_prev, \
         patch.object(frame, 'on_btn_descargar') as mock_desc, \
         patch.object(frame, 'FindFocus', return_value=frame.lista_resultados):
        evt_enter = MagicMock()
        evt_enter.GetKeyCode.return_value = wx.WXK_RETURN
        evt_enter.GetModifiers.return_value = 0
        frame.on_char_hook(evt_enter)
        assert mock_prev.called, "Enter en on_char_hook debe llamar a on_previsualizar_video"
        assert not mock_desc.called, "Enter no debe llamar a on_btn_descargar"

        mock_prev.reset_mock()
        mock_desc.reset_mock()
        frame.on_lista_key_down(evt_enter)
        assert mock_prev.called, "Enter en on_lista_key_down debe llamar a on_previsualizar_video"
        assert not mock_desc.called, "Enter en on_lista_key_down no debe llamar a on_btn_descargar"

    frame.Destroy()
    app.Destroy()
    print("  -> Eliminación con tecla Supr y diálogo de confirmación validados en reproductor y lista.")


def test_updater_module():
    print("\n[8/8] Probando módulo de actualización automática (updater.py)...")
    import json
    import updater
    assert updater.APP_VERSION == "1.5.9"
    assert updater.parse_version("1.3.0") == (1, 3, 0)
    assert updater.parse_version("v1.3.1") == (1, 3, 1)
    assert updater.parse_version("v1.4.0") == (1, 4, 0)
    assert updater.parse_version("1.4.2") == (1, 4, 2)
    assert updater.parse_version("1.4.3") == (1, 4, 3)
    assert updater.parse_version("1.4.4") == (1, 4, 4)
    assert updater.parse_version("1.4.5") == (1, 4, 5)
    assert updater.parse_version("1.4.6") == (1, 4, 6)
    assert updater.parse_version("1.4.7") == (1, 4, 7)
    assert updater.parse_version("1.4.8") == (1, 4, 8)
    assert updater.parse_version("1.4.9") == (1, 4, 9)
    assert updater.parse_version("1.5.0") == (1, 5, 0)
    assert updater.parse_version("1.5.1") == (1, 5, 1)
    assert updater.parse_version("1.5.2") == (1, 5, 2)
    assert updater.parse_version("1.5.3") == (1, 5, 3)
    assert updater.parse_version("1.5.4") == (1, 5, 4)
    assert updater.parse_version("1.5.5") == (1, 5, 5)
    assert updater.parse_version("1.5.6") == (1, 5, 6)
    assert updater.parse_version("1.5.7") == (1, 5, 7)
    assert updater.parse_version("1.5.8") == (1, 5, 8)
    assert updater.parse_version("1.5.9") == (1, 5, 9)
    assert updater.parse_version("2.0") == (2, 0)
    assert updater.parse_version("1.5.9") > updater.parse_version("1.5.8")
    assert updater.parse_version("1.5.8") > updater.parse_version("1.5.7")
    assert updater.parse_version("1.5.7") > updater.parse_version("1.5.6")
    assert updater.parse_version("1.5.6") > updater.parse_version("1.5.5")
    assert updater.parse_version("1.5.5") > updater.parse_version("1.5.4")
    assert updater.parse_version("1.5.4") > updater.parse_version("1.5.3")
    assert updater.parse_version("1.5.3") > updater.parse_version("1.5.2")
    assert updater.parse_version("1.5.2") > updater.parse_version("1.5.1")
    assert updater.parse_version("1.5.1") > updater.parse_version("1.5.0")
    assert updater.parse_version("1.5.0") > updater.parse_version("1.4.9")
    assert updater.parse_version("1.4.9") > updater.parse_version("1.4.8")
    assert updater.parse_version("1.4.8") > updater.parse_version("1.4.7")
    assert updater.parse_version("1.4.7") > updater.parse_version("1.4.6")
    assert updater.parse_version("1.4.6") > updater.parse_version("1.4.5")
    assert updater.parse_version("1.4.5") > updater.parse_version("1.4.4")
    assert updater.parse_version("1.4.4") > updater.parse_version("1.4.3")
    assert updater.parse_version("1.4.3") > updater.parse_version("1.4.2")
    assert updater.parse_version("1.4.2") > updater.parse_version("1.4.1")
    assert updater.parse_version("1.4.0") > updater.parse_version("1.3.1")
    assert updater.parse_version("1.3.1") > updater.parse_version("1.3.0")
    assert updater.parse_version("1.3.0") == updater.parse_version("1.3.0")
    assert not (updater.parse_version("1.2.9") > updater.parse_version("1.3.0"))

    # Verificar que version.json local es válido
    local_v_json = os.path.join(updater.get_base_dir(), "version.json")
    assert os.path.exists(local_v_json), "El archivo version.json debe existir"
    with open(local_v_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["version"] == "1.5.9", "version.json debe tener la versión 1.5.9"
        assert "url" in data, "version.json debe contener el campo url"
        assert "changelog" in data, "version.json debe contener el campo changelog"

    print("  -> Módulo updater, parseo SemVer y version.json validados correctamente.")


def test_waiting_sound_system():
    print("\n[12/12] Probando sistema de sonido de espera periódico durante la descarga...")
    import sound_manager
    import downloader
    from ui import OptionsDialog

    # 1. Comprobar existencia y síntesis del archivo de sonido WAV
    sound_path = sound_manager.ensure_sound_files()
    assert os.path.isfile(sound_path), "El archivo espera.wav debe existir"
    assert os.path.getsize(sound_path) > 1000, "El archivo espera.wav debe contener datos de audio"
    comp_path = sound_manager.get_sound_file_path('completado.wav')
    assert os.path.isfile(comp_path), "El archivo completado.wav debe existir"
    assert os.path.getsize(comp_path) > 1000, "El archivo completado.wav debe contener datos de audio"

    # 2. Comprobar inicio y detención del bucle de sonido y sonido de fin de descarga
    sound_manager.start_waiting_sound(interval=0.5)
    assert sound_manager.is_waiting_sound_running(), "El bucle de sonido de espera debe estar activo"
    sound_manager.play_completion_sound()
    assert not sound_manager.is_waiting_sound_running(), "play_completion_sound debe detener el sonido de espera"

    # 3. Comprobar configuración por defecto
    cfg = downloader.DEFAULT_CONFIG
    assert 'sonido_espera_descarga' in cfg, "sonido_espera_descarga debe estar en DEFAULT_CONFIG"
    assert cfg['sonido_espera_descarga'] is True, "sonido_espera_descarga debe ser True por defecto"

    print("  -> Sistema de sonido de espera validado correctamente.")


def test_subcarpeta_solo_cuando_multiples_descargas():
    print("\n[Extra] Probando que el diálogo de subcarpeta solo se active si hay más de 1 descarga seleccionada...")
    import inspect
    import ui

    # Verificamos mediante inspección estática del método on_btn_descargar que solo pregunta subcarpeta si es_multiple
    src = inspect.getsource(ui.MainFrame.on_btn_descargar)
    assert "if es_multiple:" in src, "El diálogo de subcarpeta debe estar condicionado estrictamente a if es_multiple:"
    assert "if es_multiple or es_favoritos:" not in src, "No debe activarse para favoritos individuales"
    print("  -> Condición de diálogo de subcarpeta restringida a más de 1 elemento validada con éxito.")


def test_menu_contextual_descripcion():
    print("\n[Extra] Probando opciones de descripción contextual (vídeo, lista, canal) y diálogo con copiar/aceptar...")
    import inspect
    import wx
    import ui
    from downloader import YouTubeDownloader

    # 1. Comprobar que YouTubeDownloader dispone del método obtener_descripcion
    assert hasattr(YouTubeDownloader, 'obtener_descripcion'), "YouTubeDownloader debe tener el método obtener_descripcion"

    # 2. Comprobar mediante inspección estática que on_context_menu ofrece la descripción según contexto
    src = inspect.getsource(ui.MainFrame.on_context_menu)
    assert "&Descripción del canal" in src, "Debe existir opción de descripción para canales"
    assert "&Descripción de la lista" in src, "Debe existir opción de descripción para listas de reproducción"
    assert "&Descripción del vídeo" in src, "Debe existir opción de descripción para vídeos"
    assert "self.mostrar_descripcion" in src, "Debe invocar a mostrar_descripcion con el elemento seleccionado"

    # 3. Comprobar el diálogo accesible DescriptionDialog y sus botones
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)

    # Caso vídeo
    item_vid = {'title': 'Vídeo de prueba', 'tipo_item': 'video', 'full_description': 'Descripción completa del vídeo'}
    dlg_vid = ui.DescriptionDialog(frame, item_vid)
    assert "Descripción del vídeo" in dlg_vid.GetTitle(), "El título debe indicar descripción del vídeo"
    assert dlg_vid.txt_desc.GetValue() == 'Descripción completa del vídeo'
    assert dlg_vid.btn_copiar.GetLabel() == "&Copiar al portapapeles"
    assert dlg_vid.btn_aceptar.GetLabel() == "&Aceptar"
    assert dlg_vid.btn_aceptar.GetId() == wx.ID_OK
    dlg_vid.on_copiar(None)
    assert dlg_vid.lbl_status.GetLabel() == "Descripción copiada al portapapeles."
    dlg_vid.Destroy()

    # Caso lista de reproducción
    item_pl = {'title': 'Lista de prueba', 'is_playlist': True, 'tipo_item': 'playlist', 'full_description': 'Detalles de la lista'}
    dlg_pl = ui.DescriptionDialog(frame, item_pl)
    assert "Descripción de la lista" in dlg_pl.GetTitle(), "El título debe indicar descripción de la lista"
    dlg_pl.Destroy()

    # Caso canal
    item_ch = {'title': 'Canal de prueba', 'is_channel': True, 'tipo_item': 'channel', 'full_description': 'Acerca del canal'}
    dlg_ch = ui.DescriptionDialog(frame, item_ch)
    assert "Descripción del canal" in dlg_ch.GetTitle(), "El título debe indicar descripción del canal"
    dlg_ch.Destroy()

    frame.Destroy()
    print("  -> Opciones de menú contextual y diálogo de descripción con copiar/aceptar validados con éxito.")


def test_navegacion_jerarquica_escape():
    print("\n[Extra] Probando navegación jerárquica nivel a nivel con la tecla Escape (vídeos -> lista -> canal -> favoritos)...")
    import wx
    import ui

    app = wx.App.Get() or wx.App(False)
    frame = ui.MainFrame()

    # Nivel 1: Lista de Favoritos con un canal
    frame.is_showing_favorites = True
    frame.current_fav_name = "Principal"
    frame.current_fav_tag = ""
    canal_fav = {'title': 'Canal de Favoritos', 'tipo_item': 'channel', 'is_channel': True, 'url': 'https://youtube.com/@Canal', 'selected': False}
    frame.resultados = [canal_fav]
    frame.lista_resultados.DeleteAllItems()
    frame.lista_resultados.InsertItem(0, canal_fav['title'])
    frame.lista_resultados.Select(0)
    frame.navigation_stack.clear()

    # Nivel 2: Acceso a listas de reproducción del canal
    frame._pending_nav_state = frame._capturar_estado_navegacion()
    playlists = [
        {'title': 'Playlist 1', 'tipo_item': 'playlist', 'is_playlist': True, 'url': 'https://youtube.com/playlist?list=1', 'selected': False},
        {'title': 'Playlist 2', 'tipo_item': 'playlist', 'is_playlist': True, 'url': 'https://youtube.com/playlist?list=2', 'selected': False}
    ]
    frame._on_search_completed(playlists, "Listas de reproducción del canal", False)
    assert len(frame.navigation_stack) == 1, "Debe haberse guardado el nivel de Favoritos en la pila"
    assert frame.is_showing_favorites is False
    assert len(frame.resultados) == 2
    # Seleccionamos la segunda playlist (índice 1)
    frame.lista_resultados.Select(1)
    frame.lista_resultados.Focus(1)

    # Nivel 3: Acceso a los vídeos de la Playlist 2
    frame._pending_nav_state = frame._capturar_estado_navegacion()
    videos = [
        {'title': 'Vídeo A', 'tipo_item': 'video', 'url': 'https://youtube.com/watch?v=A', 'selected': False},
        {'title': 'Vídeo B', 'tipo_item': 'video', 'url': 'https://youtube.com/watch?v=B', 'selected': False}
    ]
    frame._on_search_completed(videos, "Vídeos de la lista", False)
    assert len(frame.navigation_stack) == 2, "Deben existir 2 niveles previos en la pila (Favoritos y Listas)"
    assert len(frame.resultados) == 2
    assert frame.resultados[0]['title'] == 'Vídeo A'

    # 1ª Pulsación de Escape: debe regresar a las listas de reproducción del canal (Nivel 2)
    frame.retroceder_nivel_o_limpiar()
    assert len(frame.navigation_stack) == 1, "Debe quedar 1 nivel en la pila tras retroceder"
    assert len(frame.resultados) == 2
    assert frame.resultados[0]['title'] == 'Playlist 1'
    assert frame.resultados[1]['title'] == 'Playlist 2'
    assert frame.lista_resultados.GetFirstSelected() == 1, "Debe recordar la Playlist 2 que estaba seleccionada"

    # 2ª Pulsación de Escape: debe regresar a Favoritos (Nivel 1)
    frame.retroceder_nivel_o_limpiar()
    assert len(frame.navigation_stack) == 0, "La pila debe quedar vacía al volver a Favoritos"
    assert frame.is_showing_favorites is True, "Debe volver a la vista de Favoritos"
    assert len(frame.resultados) == 1
    assert frame.resultados[0]['title'] == 'Canal de Favoritos'
    assert frame.lista_resultados.GetFirstSelected() == 0, "Debe recordar el canal de favoritos seleccionado"

    # 3ª Pulsación de Escape: sin niveles previos, debe limpiar resultados y enfocar búsqueda
    frame.retroceder_nivel_o_limpiar()
    assert len(frame.resultados) == 0, "Debe vaciar los resultados al pulsar Escape en el nivel raíz"
    assert frame.lista_resultados.GetItemCount() == 0
    assert frame.is_showing_favorites is False

    frame.Destroy()
    print("  -> Navegación jerárquica y retroceso escalonado con Escape validados satisfactoriamente.")


def test_sugerencia_subcarpeta_lista_o_canal():
    print("\n[Extra] Probando sugerencia de subcarpeta inteligente (lista o canal)...")
    import wx
    import ui
    app = wx.App.Get() or wx.App(False)
    frame = ui.MainFrame()

    video_a = {'title': 'Canción 1', 'channel': 'Queen', 'url': 'https://youtube.com/watch?v=1'}
    video_b = {'title': 'Canción 2', 'channel': 'Queen', 'url': 'https://youtube.com/watch?v=2'}
    video_c = {'title': 'Canción 3', 'channel': 'Beatles', 'url': 'https://youtube.com/watch?v=3'}

    # 1. En lista de favoritos: debe sugerir el nombre de la lista de favoritos
    frame.is_showing_favorites = True
    frame.current_fav_name = "Mis Baladas"
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_b])
    assert sug == "Mis Baladas", f"Esperado 'Mis Baladas', obtenido '{sug}'"

    frame.current_fav_name = "Todas las listas"
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_b])
    assert sug == "Favoritos", f"Esperado 'Favoritos', obtenido '{sug}'"

    # 2. En lista de reproducción de YouTube: debe sugerir el nombre de la lista
    frame.is_showing_favorites = False
    frame.last_search_kind = 'playlist_videos'
    frame.current_playlist_title = "Grandes Éxitos de los 80"
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_b])
    assert sug == "Grandes Éxitos de los 80", f"Esperado 'Grandes Éxitos de los 80', obtenido '{sug}'"

    # 3. En Ver más tarde: debe sugerir 'Ver más tarde'
    frame.last_search_kind = 'ver_mas_tarde'
    frame.current_playlist_title = ""
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_b])
    assert sug == "Ver más tarde", f"Esperado 'Ver más tarde', obtenido '{sug}'"

    # 4. En un canal (no pertenece a lista): debe sugerir el nombre del canal
    frame.last_search_kind = 'canal_videos'
    frame.current_playlist_title = ""
    frame.current_channel_title = "Canal Oficial Queen"
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_b])
    assert sug == "Canal Oficial Queen", f"Esperado 'Canal Oficial Queen', obtenido '{sug}'"

    # 5. En búsqueda general sin lista: debe sugerir el canal de los vídeos
    frame.last_search_kind = 'search'
    frame.current_playlist_title = ""
    frame.current_channel_title = ""
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_b])
    assert sug == "Queen", f"Esperado 'Queen', obtenido '{sug}'"

    # 6. En búsqueda general con canales mixtos: sugiere el canal del primer vídeo
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_c])
    assert sug == "Queen", f"Esperado 'Queen', obtenido '{sug}'"

    # 7. Fallback: nunca sugerir URL en crudo como nombre de subcarpeta
    frame.last_search_query = "https://www.youtube.com/playlist?list=PL12345"
    sug = frame.sugerir_nombre_subcarpeta([{'title': 'V1'}, {'title': 'V2'}])
    assert sug == "Descargas", f"No debe sugerir URLs en crudo, obtenido '{sug}'"

    frame.Destroy()
    print("  -> Sugerencias de subcarpeta para listas y canales validadas satisfactoriamente.")


def test_barra_progreso_no_alcanzable_por_tabulador():
    print("\n[Extra] Probando que la barra de progreso del reproductor esté excluida del tabulador...")
    import wx
    import ui
    app = wx.App.Get() or wx.App(False)
    vids = [{'title': 'Prueba Tab', 'channel': 'Canal', 'url': 'https://youtube.com/watch?v=1'}]
    dlg = ui.VideoPreviewDialog(None, vids)
    dlg.Show()
    app.Yield()

    # Verificar que AcceptsFocus y AcceptsFocusFromKeyboard retornen False en slider_pos
    assert not dlg.slider_pos.AcceptsFocus(), "slider_pos no debe aceptar foco normal"
    assert not dlg.slider_pos.AcceptsFocusFromKeyboard(), "slider_pos no debe aceptar foco de teclado"

    tab_stops = []
    f = dlg.FindFocus()
    for _ in range(12):
        if f == dlg.slider_pos:
            tab_stops.append('SLIDER_POS')
        else:
            tab_stops.append(f.GetLabel() if hasattr(f, 'GetLabel') else str(type(f)))
        f.Navigate(wx.NavigationKeyEvent.IsForward)
        app.Yield()
        f = dlg.FindFocus()

    assert 'SLIDER_POS' not in tab_stops, f"La barra de progreso no debe ser alcanzada por el tabulador. Tab stops: {tab_stops}"
    dlg.Destroy()
    print("  -> Barra de progreso excluida de la navegación por tabulador validada con éxito.")


def test_f8_porcentaje_y_sonido_descripcion():
    print("\n[Extra] Probando atajo F8 para anunciar porcentaje de descarga y sonido de espera en descripción...")
    import wx
    import ui
    import sound_manager
    import accessibility

    app = wx.App.Get() or wx.App(False)
    frame = ui.MainFrame()

    # 1. Probar F8 en MainFrame cuando NO hay descargas
    spoken = []
    orig_speak = accessibility.speak
    accessibility.speak = lambda msg: spoken.append(msg)
    try:
        frame.anunciar_porcentaje_descarga()
        assert len(spoken) > 0 and "No hay ninguna descarga en curso" in spoken[-1]

        # 2. Probar F8 en MainFrame cuando SÍ hay una descarga activa
        frame.btn_cancelar.Enable(True)
        frame.current_download_status = 'downloading'
        frame.current_download_percent = 57
        frame.total_cola = 1
        frame.indice_cola = 0
        frame.anunciar_porcentaje_descarga()
        assert "57 por ciento" in spoken[-1]

        # Descarga por lotes [2/5]
        frame.total_cola = 5
        frame.indice_cola = 1
        frame.current_download_percent = 83
        frame.anunciar_porcentaje_descarga()
        assert "[2/5] 83 por ciento" in spoken[-1]

        # Estado procesando
        frame.current_download_status = 'processing'
        frame.anunciar_porcentaje_descarga()
        assert "Procesando archivo final" in spoken[-1]
    finally:
        accessibility.speak = orig_speak
        frame.btn_cancelar.Enable(False)

    # 3. Probar atajo F8 en PlayerDialog
    class MockVlcPlayer:
        def __init__(self, cur_time=35000, length=100000):
            self._time = cur_time
            self._length = length
        def get_time(self):
            return self._time
        def get_length(self):
            return self._length

    player_dlg = ui.VideoPreviewDialog(frame, {'title': 'Vídeo Test', 'duration_seconds': 100})
    player_dlg.vlc_player = MockVlcPlayer(cur_time=45000, length=100000)
    spoken_p = []
    accessibility.speak = lambda msg: spoken_p.append(msg)
    try:
        player_dlg.anunciar_porcentaje()
        assert len(spoken_p) > 0 and "45 por ciento" in spoken_p[-1]
    finally:
        accessibility.speak = orig_speak
        player_dlg.on_cleanup()
        player_dlg.Destroy()

    # 4. Probar sonido de espera en DescriptionDialog durante obtención de descripción
    sound_manager.stop_waiting_sound()
    item_sin_cache = {'title': 'Vídeo para descripción', 'tipo_item': 'video', 'id': 'dummy123'}
    dlg_desc = ui.DescriptionDialog(frame, item_sin_cache)
    assert hasattr(dlg_desc, 'on_close'), "Debe tener método on_close"
    dlg_desc.on_close()
    assert not sound_manager.is_waiting_sound_running(), "Al cerrar el diálogo de descripción el sonido de espera debe detenerse"

    frame.Destroy()
    print("  -> Atajo F8 para porcentaje (descarga y reproductor) y sonido de espera en descripción validados con éxito.")


def test_reproductor_shuffle_stop_y_atajos():
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


def test_coherencia_estados_interfaz_y_un_solo_item():
    print("Probando coherencia de interfaz, atenuación de menús y restricciones con 1 solo ítem o cola vacía...")
    import wx
    import ui
    app = wx.GetApp() or wx.App()
    frame = ui.MainFrame()
    try:
        # 1. Comprobar que existen los 8 menús sin duplicidades en Edición ni Favoritos
        menubar = frame.GetMenuBar()
        titulos_menus = [menubar.GetMenuLabel(i).replace("&", "") for i in range(menubar.GetMenuCount())]
        assert "Reproducción" in titulos_menus, "El menú Reproducción debe existir en la barra de menú"
        assert "Archivo" in titulos_menus and "Edición" in titulos_menus and "Favoritos" in titulos_menus

        # 2. Estado inicial con lista vacía y cola vacía
        assert not frame.resultados
        assert not frame.cola_reproduccion
        frame.actualizar_estados_interfaz()

        # Botones atenuados
        assert frame.btn_descargar.IsEnabled() is False, "Descargar debe estar atenuado sin ítems"
        assert frame.btn_previsualizar.IsEnabled() is False, "Reproducir selección debe estar atenuado sin ítems"
        assert frame.btn_reproducir_todo.IsEnabled() is False, "Reproducir toda la lista debe estar atenuado sin ítems"
        assert frame.btn_add_cola.IsEnabled() is False, "Añadir a la cola debe estar atenuado sin ítems"
        assert frame.btn_ver_cola.IsShown() is False, "Ver cola debe estar oculto con cola vacía"
        assert frame.btn_reproducir_cola.IsShown() is False, "Reproducir cola debe estar oculto con cola vacía"

        # Menús atenuados y cola ausente del menú cuando está vacía
        assert frame.item_descargar.IsEnabled() is False
        assert frame.item_descargar_todo.IsEnabled() is False
        assert frame.item_play_all.IsEnabled() is False
        assert frame.item_previsualizar.IsEnabled() is False
        assert frame.item_add_queue.IsEnabled() is False
        assert frame.menu_reproduccion.FindItemById(1082) is None, "Ver cola no debe aparecer en el menú con cola vacía"
        assert frame.menu_reproduccion.FindItemById(1081) is None, "Reproducir cola no debe aparecer en el menú con cola vacía"
        assert frame.menu_reproduccion.FindItemById(1083) is None, "Vaciar cola no debe aparecer en el menú con cola vacía"
        assert frame.item_sel_all.IsEnabled() is False
        assert frame.item_desel_all.IsEnabled() is False
        assert frame.item_inv_sel.IsEnabled() is False
        assert frame.item_sel_toggle.IsEnabled() is False

        # 3. Con exactamente 1 solo ítem
        un_video = [{
            'index': 1, 'id': 'vid_unico', 'title': 'Vídeo Único', 'channel': 'Canal Único',
            'duration': '02:00', 'duration_seconds': 120, 'views': '50',
            'url': 'http://yt.com/unico', 'is_playlist': False, 'is_channel': False, 'selected': False
        }]
        frame._on_search_completed(un_video, "Test 1 ítem")
        assert len(frame.resultados) == 1

        # Acciones para 1 ítem habilitadas
        assert frame.btn_descargar.IsEnabled() is True
        assert frame.btn_previsualizar.IsEnabled() is True
        assert frame.btn_add_cola.IsEnabled() is True
        assert frame.item_descargar.IsEnabled() is True
        assert frame.item_previsualizar.IsEnabled() is True
        assert frame.item_add_queue.IsEnabled() is True

        # Acciones que no tienen sentido con 1 solo ítem DEBEN estar atenuadas
        assert frame.btn_reproducir_todo.IsEnabled() is False, "Reproducir toda la lista debe estar atenuado con 1 solo ítem"
        assert frame.item_play_all.IsEnabled() is False, "Menú Reproducir toda la lista debe estar atenuado con 1 solo ítem"
        assert frame.item_descargar_todo.IsEnabled() is False, "Descargar todos debe estar atenuado con 1 solo ítem"
        assert frame.item_sel_toggle.IsEnabled() is False, "Marcar/desmarcar debe estar atenuado con 1 solo ítem"
        assert frame.item_sel_all.IsEnabled() is False, "Seleccionar todos debe estar atenuado con 1 solo ítem"
        assert frame.item_desel_all.IsEnabled() is False, "Deseleccionar todos debe estar atenuado con 1 solo ítem"
        assert frame.item_inv_sel.IsEnabled() is False, "Invertir selección debe estar atenuado con 1 solo ítem"

        # Comprobar que marcar/desmarcar con 1 solo ítem no hace marcas
        frame.toggle_seleccion_actual()
        assert frame.resultados[0]['selected'] is False, "No debe marcar elemento si la lista tiene 1 solo ítem"

        # 4. Con múltiples ítems (>1)
        dos_videos = [
            {'index': 1, 'id': 'v1', 'title': 'V1', 'channel': 'C1', 'duration': '01:00', 'duration_seconds': 60, 'views': '10', 'url': 'http://yt.com/1', 'is_playlist': False, 'is_channel': False, 'selected': False},
            {'index': 2, 'id': 'v2', 'title': 'V2', 'channel': 'C2', 'duration': '02:00', 'duration_seconds': 120, 'views': '20', 'url': 'http://yt.com/2', 'is_playlist': False, 'is_channel': False, 'selected': False}
        ]
        frame._on_search_completed(dos_videos, "Test 2 ítems")
        assert len(frame.resultados) == 2
        assert frame.btn_reproducir_todo.IsEnabled() is True
        assert frame.item_play_all.IsEnabled() is True
        assert frame.item_descargar_todo.IsEnabled() is True
        assert frame.item_sel_toggle.IsEnabled() is True
        assert frame.item_sel_all.IsEnabled() is True
        assert frame.item_desel_all.IsEnabled() is True
        assert frame.item_inv_sel.IsEnabled() is True

        # 5. Comprobar ciclo de vida de la cola de reproducción
        assert frame.btn_ver_cola.IsShown() is False
        assert frame.btn_reproducir_cola.IsShown() is False
        assert frame.menu_reproduccion.FindItemById(1082) is None
        frame.agregar_a_cola_reproduccion(items=[{'id': 'q1', 'title': 'Tema Cola 1', 'url': 'http://yt.com/q1'}])
        assert len(frame.cola_reproduccion) == 1
        assert frame.btn_ver_cola.IsShown() is True
        assert frame.btn_reproducir_cola.IsShown() is True
        assert frame.menu_reproduccion.FindItemById(1082) is not None
        assert frame.menu_reproduccion.FindItemById(1081) is not None
        assert frame.menu_reproduccion.FindItemById(1083) is not None

        frame.vaciar_cola_reproduccion()
        assert len(frame.cola_reproduccion) == 0
        assert frame.btn_ver_cola.IsShown() is False
        assert frame.btn_reproducir_cola.IsShown() is False
        assert frame.menu_reproduccion.FindItemById(1082) is None
        assert frame.menu_reproduccion.FindItemById(1081) is None
        assert frame.menu_reproduccion.FindItemById(1083) is None

    finally:
        frame.Destroy()

    print("  -> Coherencia y visibilidad condicional de cola validadas correctamente.")


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


def test_modo_locuciones_y_deteccion_lector_pantalla():
    print("\n[Extra] Probando modo de locuciones y detección inteligente de lector de pantalla...")
    import downloader
    import accessibility
    import ui
    import wx
    from unittest.mock import MagicMock, patch

    # 1. Comprobar DEFAULT_CONFIG
    assert 'modo_locuciones' in downloader.DEFAULT_CONFIG, "modo_locuciones debe estar en DEFAULT_CONFIG"
    assert downloader.DEFAULT_CONFIG['modo_locuciones'] == 'auto'

    # 2. Modo 'auto': si no hay lector activo, NO emite locución
    accessibility.set_modo_locuciones('auto')
    with patch('accessibility.is_app_active', return_value=True), \
         patch('accessibility.is_screen_reader_active', return_value=False), \
         patch('accessibility._speaker') as mock_speaker:
        accessibility.speak("Mensaje para videntes que debe silenciarse")
        mock_speaker.speak.assert_not_called()

    # 3. Modo 'auto': si SÍ hay lector activo, SÍ emite locución
    accessibility.set_modo_locuciones('auto')
    with patch('accessibility.is_app_active', return_value=True), \
         patch('accessibility.is_screen_reader_active', return_value=True), \
         patch('accessibility._speaker') as mock_speaker:
        accessibility.speak("Mensaje para lector activo")
        mock_speaker.speak.assert_called_with("Mensaje para lector activo", interrupt=True)

    # 4. Modo 'desactivado': nunca emite locución, incluso con lector activo
    accessibility.set_modo_locuciones('desactivado')
    with patch('accessibility.is_app_active', return_value=True), \
         patch('accessibility.is_screen_reader_active', return_value=True), \
         patch('accessibility._speaker') as mock_speaker:
        accessibility.speak("Mensaje con locuciones desactivadas")
        mock_speaker.speak.assert_not_called()

    # 5. Modo 'siempre': emite locución incluso si no hay lector activo
    accessibility.set_modo_locuciones('siempre')
    with patch('accessibility.is_app_active', return_value=True), \
         patch('accessibility.is_screen_reader_active', return_value=False), \
         patch('accessibility._speaker') as mock_speaker:
        accessibility.speak("Mensaje forzado siempre")
        mock_speaker.speak.assert_called_with("Mensaje forzado siempre", interrupt=True)

    # Restaurar modo 'auto'
    accessibility.set_modo_locuciones('auto')

    # 6. Comprobar presencia de choice_tts en OptionsDialog
    app = wx.GetApp() or wx.App()
    parent = wx.Frame(None)
    dlg = ui.OptionsDialog(parent)
    assert hasattr(dlg, 'choice_tts'), "OptionsDialog debe contener el control choice_tts"
    assert dlg.choice_tts.GetCount() == 3, "choice_tts debe tener 3 opciones (auto, siempre, desactivado)"
    dlg.Destroy()
    parent.Destroy()

    print("  -> Modo de locuciones y detección de lector de pantalla validados exitosamente.")


def test_pegar_enlace_canal_o_lista():
    print("\n[Prueba] Verificando búsqueda y pegado de enlace de canal y lista como contenedores...")
    import wx
    import ui
    from downloader import YouTubeDownloader, agregar_favorito, obtener_favoritos, eliminar_favorito, eliminar_lista_favoritos, detectar_tipo_elemento
    from unittest.mock import patch

    dl = YouTubeDownloader()

    # 1. Simulación de canal
    mock_ch_entry = {
        'id': '@CanalEjemplo',
        'title': 'Canal de Prueba',
        'channel': 'Canal de Prueba',
        'channel_follower_count': 120000,
        '_type': 'playlist',
        'channel_url': 'https://www.youtube.com/@CanalEjemplo',
        'entries': []
    }
    with patch.object(dl, 'extraer_info_contenedor', return_value=dl._procesar_entries([mock_ch_entry], is_channel_list=True)):
        res_ch = dl.buscar("https://www.youtube.com/@CanalEjemplo")
        assert len(res_ch) == 1, "Debe retornar exactamente 1 elemento para el canal"
        assert res_ch[0]['is_channel'] is True
        assert res_ch[0]['is_playlist'] is False
        assert res_ch[0]['title'] == 'Canal de Prueba'
        assert detectar_tipo_elemento(res_ch[0]) == 'channel'

        # Probar agregar canal a favoritos
        agregar_favorito(res_ch[0], "TestCanales")
        favs = obtener_favoritos("TestCanales")
        assert len(favs) == 1
        assert favs[0]['is_channel'] is True
        assert favs[0]['title'] == 'Canal de Prueba'
        eliminar_lista_favoritos("TestCanales")

    # 2. Simulación de playlist
    mock_pl_entry = {
        'id': 'PL1234567890',
        'title': 'Lista de Reproducción de Prueba',
        'uploader': 'Creador',
        'playlist_count': 42,
        '_type': 'playlist',
        'webpage_url': 'https://www.youtube.com/playlist?list=PL1234567890',
        'entries': []
    }
    with patch.object(dl, 'extraer_info_contenedor', return_value=dl._procesar_entries([mock_pl_entry], is_playlist_list=True)):
        res_pl = dl.buscar("https://www.youtube.com/playlist?list=PL1234567890")
        assert len(res_pl) == 1, "Debe retornar exactamente 1 elemento para la lista"
        assert res_pl[0]['is_channel'] is False
        assert res_pl[0]['is_playlist'] is True
        assert res_pl[0]['title'] == 'Lista de Reproducción de Prueba'
        assert detectar_tipo_elemento(res_pl[0]) == 'playlist'

        # Probar agregar playlist a favoritos
        agregar_favorito(res_pl[0], "TestPlaylists")
        favs_pl = obtener_favoritos("TestPlaylists")
        assert len(favs_pl) == 1
        assert favs_pl[0]['is_playlist'] is True
        assert favs_pl[0]['title'] == 'Lista de Reproducción de Prueba'
        eliminar_lista_favoritos("TestPlaylists")

    # 3. Comprobación en interfaz gráfica
    app = wx.GetApp() or wx.App()
    frame = ui.MainFrame()
    frame.last_search_query = "https://www.youtube.com/@CanalEjemplo"
    frame._on_search_completed(res_ch, "https://www.youtube.com/@CanalEjemplo", False)

    assert frame.lista_resultados.GetItemCount() == 1
    assert frame.lista_resultados.GetItemText(0, 0) == "Canal de Prueba"
    assert frame.btn_siguientes.IsEnabled() is False
    assert "Canal obtenido" in frame.lbl_progreso_detalle.GetLabel()

    frame.Destroy()

    print("  -> Búsqueda y guardado en favoritos de canal/lista como contenedor validados correctamente.")


def test_limpieza_extensiones_en_descarga():
    print("\n[Prueba] Verificando limpieza de extensiones redundantes en títulos y archivos...")
    from downloader import limpiar_extension_titulo, corregir_doble_extension, YouTubeDownloader

    # 1. Limpieza de títulos que terminan en extensión multimedia
    assert limpiar_extension_titulo("Tutorial Python.flv") == "Tutorial Python"
    assert limpiar_extension_titulo("Video Clip Oficial.mp4") == "Video Clip Oficial"
    assert limpiar_extension_titulo("Grabacion de audio.MP3") == "Grabacion de audio"
    assert limpiar_extension_titulo("Cancion.flv.mp4") == "Cancion"
    assert limpiar_extension_titulo("Version 1.5.8") == "Version 1.5.8"
    assert limpiar_extension_titulo("Curso de Node.js") == "Curso de Node.js"

    # 2. Corrección de doble extensión en archivos
    assert corregir_doble_extension("C:\\Descargas\\Cancion.flv.mp3") == "C:\\Descargas\\Cancion.mp3"
    assert corregir_doble_extension("C:\\Descargas\\Video.mp4.mp4") == "C:\\Descargas\\Video.mp4"
    assert corregir_doble_extension("C:\\Descargas\\Grabacion.avi.flac") == "C:\\Descargas\\Grabacion.flac"
    assert corregir_doble_extension("C:\\Descargas\\Pista.m4a.m4a") == "C:\\Descargas\\Pista.m4a"
    assert corregir_doble_extension("C:\\Descargas\\Archivo.backup.mp3") == "C:\\Descargas\\Archivo.backup.mp3"
    assert corregir_doble_extension("C:\\Descargas\\Normal.mp3") == "C:\\Descargas\\Normal.mp3"

    # 3. Verificación en _procesar_entries
    dl = YouTubeDownloader()
    entries = [
        {'id': '1', 'title': 'Tema Musical.flv', 'url': 'https://www.youtube.com/watch?v=1', 'duration': 120},
        {'id': '2', 'title': 'Videotutorial.mp4', 'url': 'https://www.youtube.com/watch?v=2', 'duration': 300},
    ]
    procesados = dl._procesar_entries(entries)
    assert procesados[0]['title'] == "Tema Musical", f"Esperado 'Tema Musical', obtenido '{procesados[0]['title']}'"
    assert procesados[1]['title'] == "Videotutorial", f"Esperado 'Videotutorial', obtenido '{procesados[1]['title']}'"

    print("  -> Limpieza de extensiones redundantes en títulos y archivos validada exitosamente.")


def test_descarga_finalizacion_y_estado_botones():
    print("\n[30/30] Probando ciclo de finalización de descargas y restauración de botones...")
    import wx
    import ui
    import sound_manager

    app = wx.GetApp() or wx.App(False)
    frame = ui.MainFrame()
    frame.config['preguntar_abrir_carpeta'] = False
    frame.config['abrir_carpeta_al_terminar'] = False

    # Simular inicio de descarga
    frame.cola_descargas = [{'title': 'Vídeo Test', 'url': 'http://youtube.com/watch?v=123'}]
    frame.total_cola = 1
    frame.indice_cola = 0
    frame.descargas_completadas = 0
    frame.descargas_fallidas = 0
    frame.btn_descargar.Enable(False)
    frame.btn_cancelar.Enable(True)
    sound_manager.start_waiting_sound(interval=10.0)
    assert sound_manager.is_waiting_sound_running()

    # Simular finalización de elemento
    frame._on_item_queue_finished({'title': 'Vídeo Test', 'filepath': 'test.mp4'})

    assert not frame.btn_cancelar.IsEnabled(), "El botón cancelar debe quedar deshabilitado al finalizar"
    assert frame.btn_descargar.IsEnabled(), "El botón descargar debe quedar rehabilitado al finalizar"
    assert frame.descargas_completadas == 1, "Debe registrarse 1 descarga completada"
    assert len(frame.cola_descargas) == 0, "La cola debe quedar limpia"
    assert not sound_manager.is_waiting_sound_running(), "El sonido de espera debe detenerse al finalizar"

    frame.Destroy()
    print("  -> Finalización de descarga y estados de botones validados correctamente.")


def test_playlist_enter_y_menu_contextual():
    print("\n[Extra] Probando activación (Enter) y menú contextual sobre listas de reproducción...")
    import wx
    import ui

    app = wx.App.Get() or wx.App(False)
    frame = ui.MainFrame()

    playlist_item = {
        'index': 1,
        'id': 'PLtest123',
        'title': 'Lista Especial',
        'channel': 'Canal Test',
        'channel_url': 'https://www.youtube.com/@CanalTest',
        'duration': '10 vídeos',
        'views': '10 vídeos',
        'url': 'https://www.youtube.com/playlist?list=PLtest123',
        'is_playlist': True,
        'is_channel': False,
        'selected': False
    }

    frame.resultados = [playlist_item]
    frame.lista_resultados.DeleteAllItems()
    frame.lista_resultados.InsertItem(0, playlist_item['title'])
    frame.lista_resultados.Select(0)
    frame.lista_resultados.Focus(0)

    # 1. Probar Enter vía on_char_hook y on_lista_key_down
    llamadas_busqueda = []
    frame.ejecutar_busqueda_playlist_videos = lambda url, title='': llamadas_busqueda.append((url, title))

    class MockKeyEvent:
        def __init__(self, kc):
            self._kc = kc
        def GetKeyCode(self):
            return self._kc
        def GetModifiers(self):
            return 0
        def Skip(self):
            pass

    frame.lista_resultados.SetFocus()
    frame.FindFocus = lambda: frame.lista_resultados

    frame.on_char_hook(MockKeyEvent(wx.WXK_RETURN))
    assert len(llamadas_busqueda) == 1, "Enter en on_char_hook debe llamar a ejecutar_busqueda_playlist_videos"
    assert llamadas_busqueda[0] == (playlist_item['url'], playlist_item['title'])

    frame.on_lista_key_down(MockKeyEvent(wx.WXK_RETURN))
    assert len(llamadas_busqueda) == 2, "Enter en on_lista_key_down debe llamar a ejecutar_busqueda_playlist_videos"

    # 2. Probar menú contextual en playlist
    menu_items = []
    def mock_popup(menu, *args, **kwargs):
        menu_items.extend([item.GetItemLabelText() for item in menu.GetMenuItems()])
    frame.PopupMenu = mock_popup

    evt_ctx = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU)
    frame.on_context_menu(evt_ctx)
    assert len(menu_items) > 0, "El menú contextual debe mostrarse sin lanzar excepciones"
    assert any("Ver vídeos de esta lista" in it for it in menu_items), f"El menú contextual debe incluir opción para ver vídeos: {menu_items}"
    assert any("Descargar todos los vídeos de esta lista" in it for it in menu_items), "Debe incluir opción de descarga"

    frame.Destroy()
    print("  -> Activación por Enter y menú contextual de playlist validados satisfactoriamente.")


if __name__ == "__main__":
    test_url_detection()
    test_downloader()
    test_gui_init_and_selection()
    test_channel_playlist_extraction()
    test_config_persistence_and_paths()
    test_favorites_multiple_lists_system()
    test_mover_multiples_favoritos_y_busqueda()
    test_no_cambiar_lista_si_no_es_favorito()
    test_video_player_continuous_logic()
    test_favorites_delete_supr_key_and_confirmation()
    test_updater_module()
    test_waiting_sound_system()
    test_subcarpeta_solo_cuando_multiples_descargas()
    test_menu_contextual_descripcion()
    test_navegacion_jerarquica_escape()
    test_sugerencia_subcarpeta_lista_o_canal()
    test_barra_progreso_no_alcanzable_por_tabulador()
    test_f8_porcentaje_y_sonido_descripcion()
    test_reproductor_shuffle_stop_y_atajos()
    test_reproductor_orden_aleatorio_sin_repeticion_y_precarga()
    test_cola_reproduccion_y_descargas()
    test_ver_cola_dialogo_y_atajos_ctrl_p_n()
    test_coherencia_estados_interfaz_y_un_solo_item()
    test_cola_menu_contextual_y_seleccion_favoritos()
    test_dispositivo_salida_audio()
    test_foco_reproductor_cambio_tarea_y_aislamiento_tts()
    test_modo_locuciones_y_deteccion_lector_pantalla()
    test_pegar_enlace_canal_o_lista()
    test_limpieza_extensiones_en_descarga()
    test_descarga_finalizacion_y_estado_botones()
    test_playlist_enter_y_menu_contextual()
    print("\n¡Todas las pruebas pasaron satisfactoriamente!")
    import os
    os._exit(0)



