"""
Runner principal de la suite de pruebas funcionales.
Ejecuta todos los módulos organizados en el paquete tests/.
"""
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from tests.test_downloader import (
    test_url_detection,
    test_downloader,
    test_channel_playlist_extraction,
    test_subcarpeta_solo_cuando_multiples_descargas,
    test_sugerencia_subcarpeta_lista_o_canal,
    test_limpieza_extensiones_en_descarga,
    test_descarga_finalizacion_y_estado_botones,
)
from tests.test_ui import (
    test_gui_init_and_selection,
    test_config_persistence_and_paths,
    test_waiting_sound_system,
    test_menu_contextual_descripcion,
    test_navegacion_jerarquica_escape,
    test_barra_progreso_no_alcanzable_por_tabulador,
    test_f8_porcentaje_y_sonido_descripcion,
    test_coherencia_estados_interfaz_y_un_solo_item,
    test_modo_locuciones_y_deteccion_lector_pantalla,
    test_pegar_enlace_canal_o_lista,
    test_playlist_enter_y_menu_contextual,
)
from tests.test_favorites import (
    test_favorites_multiple_lists_system,
    test_mover_multiples_favoritos_y_busqueda,
    test_no_cambiar_lista_si_no_es_favorito,
    test_favorites_delete_supr_key_and_confirmation,
    test_navegacion_jerarquica_mis_listas_favoritos,
)
from tests.test_player import (
    test_video_player_continuous_logic,
    test_reproductor_shuffle_stop_y_atajos,
    test_reproductor_orden_aleatorio_sin_repeticion_y_precarga,
    test_cola_reproduccion_y_descargas,
    test_ver_cola_dialogo_y_atajos_ctrl_p_n,
    test_cola_menu_contextual_y_seleccion_favoritos,
    test_dispositivo_salida_audio,
    test_foco_reproductor_cambio_tarea_y_aislamiento_tts,
)
from tests.test_updater import (
    test_updater_module,
)

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
    test_navegacion_jerarquica_mis_listas_favoritos()
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
    os._exit(0)
