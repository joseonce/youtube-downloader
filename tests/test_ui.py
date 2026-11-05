"""
Tests modulares del sistema.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_gui_init_and_selection():
    print("\n[3/6] Probando inicialización de la interfaz wxPython (Descargador de YouTube), selector de búsqueda y manual...")
    import wx
    import accessibility
    from unittest.mock import patch
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

    # Probar cambio puntual de tipo de búsqueda en la barra (no altera config.json persistente) y anuncio sin la palabra 'tipo'
    initial_saved_type = frame.config.get('search_type_idx', 0)
    anuncios_tipo = []
    with patch('ui.accessibility.speak', side_effect=lambda msg: anuncios_tipo.append(msg)):
        frame.choice_tipo_busqueda.SetSelection(1)
        frame.on_tipo_busqueda_changed()
        assert frame.choice_tipo_busqueda.GetSelection() == 1
        assert anuncios_tipo[-1] == "Canales"
        frame.choice_tipo_busqueda.SetSelection(0)
        frame.on_tipo_busqueda_changed()
        assert anuncios_tipo[-1] == "Vídeos"
        frame.choice_tipo_busqueda.SetSelection(2)
        frame.on_tipo_busqueda_changed()
        assert anuncios_tipo[-1] == "Listas"
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
        # Verificar etiquetas accesibles al final (permiten navegación por primera letra y mejor lectura)
        assert frame.lista_resultados.GetItemText(0, 0) == "Video Favorito [Vídeo]"
        assert frame.lista_resultados.GetItemText(1, 0) == "Canal Favorito [Canal]"
        assert frame.lista_resultados.GetItemText(2, 0) == "Playlist Favorita [Lista]"
        # Verificar imágenes/iconos asociados
        assert frame.lista_resultados.GetItem(0, 0).GetImage() == frame.IMG_IDX_VIDEO
        assert frame.lista_resultados.GetItem(1, 0).GetImage() == frame.IMG_IDX_CHANNEL
        assert frame.lista_resultados.GetItem(2, 0).GetImage() == frame.IMG_IDX_PLAYLIST
        # Verificar marcado con Espacio manteniendo la etiqueta
        frame.lista_resultados.Select(1)
        frame.toggle_seleccion_actual()
        assert frame.lista_resultados.GetItemText(1, 0) == "Marcado - Canal Favorito [Canal]"

        # Probar navegación por primera letra ignorando marcas y etiquetas
        class DummyKeyEvt:
            def __init__(self, kc):
                self.kc = kc
            def GetKeyCode(self):
                return self.kc
            def GetModifiers(self):
                return 0
            def Skip(self):
                pass

        frame.on_lista_key_down(DummyKeyEvt(ord('P')))
        assert frame.lista_resultados.GetFirstSelected() == 2
        frame.on_lista_key_down(DummyKeyEvt(ord('V')))
        assert frame.lista_resultados.GetFirstSelected() == 0
        frame.on_lista_key_down(DummyKeyEvt(ord('C')))
        assert frame.lista_resultados.GetFirstSelected() == 1
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


    # Restaurar configuración inicial limpia por defecto
    cfg_restored = dict(DEFAULT_CONFIG)
    guardar_configuracion(cfg_restored)
    print(f"  -> Estructura modular validada (config/, bin/, docs/, resources/) y config.json restaurado con valores predeterminados en: {cfg_file}")


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
    import favorites_manager

    orig_nombres = favorites_manager.obtener_nombres_listas_favoritos
    favorites_manager.obtener_nombres_listas_favoritos = lambda: ['Principal']

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

    favorites_manager.obtener_nombres_listas_favoritos = orig_nombres
    frame.Destroy()
    print("  -> Navegación jerárquica y retroceso escalonado con Escape validados satisfactoriamente.")


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


if __name__ == '__main__':
    test_gui_init_and_selection()
    test_config_persistence_and_paths()
    test_waiting_sound_system()
    test_menu_contextual_descripcion()
    test_navegacion_jerarquica_escape()
    test_barra_progreso_no_alcanzable_por_tabulador()
    test_f8_porcentaje_y_sonido_descripcion()
    test_coherencia_estados_interfaz_y_un_solo_item()
    test_modo_locuciones_y_deteccion_lector_pantalla()
    test_pegar_enlace_canal_o_lista()
    test_playlist_enter_y_menu_contextual()
    print("\n[OK] Todas las pruebas de test_ui.py pasaron satisfactoriamente.")
    import os
    os._exit(0)
