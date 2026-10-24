"""
Módulo gestor de efectos de sonido y señalización sonora para la aplicación.
Proporciona sonidos de espera y respuesta auditiva no intrusivos,
especialmente útiles para usuarios con lectores de pantalla (NVDA, JAWS)
y para indicar procesos en segundo plano.
"""

import os
import sys
import math
import struct
import wave
import threading

try:
    import winsound
except ImportError:
    winsound = None


_waiting_thread = None
_stop_event = threading.Event()
_lock = threading.Lock()
_configured_audio_device = ''
_vlc_sound_player = None
_vlc_sound_instance = None


def set_audio_device(device_id=''):
    """Establece el dispositivo de salida de audio para los efectos sonoros."""
    global _configured_audio_device, _vlc_sound_player
    with _lock:
        _configured_audio_device = device_id or ''
        if _vlc_sound_player:
            try:
                _vlc_sound_player.audio_output_device_set(None, _configured_audio_device)
            except Exception:
                pass


def get_audio_device():
    """Retorna el identificador del dispositivo de salida de audio configurado."""
    global _configured_audio_device
    with _lock:
        return _configured_audio_device


def _get_vlc_for_sound():
    try:
        import ui
        return ui.get_vlc_module()
    except Exception:
        try:
            import vlc
            return vlc
        except Exception:
            return None


def _play_vlc_sound_file(path, audio_dev, volume=90):
    global _vlc_sound_instance, _vlc_sound_player
    vlc_mod = _get_vlc_for_sound()
    if not vlc_mod:
        if winsound:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        return
    try:
        if _vlc_sound_instance is None:
            _vlc_sound_instance = vlc_mod.Instance('--quiet')
        if _vlc_sound_player is None:
            _vlc_sound_player = _vlc_sound_instance.media_player_new()
        if audio_dev:
            try:
                _vlc_sound_player.audio_output_device_set(None, audio_dev)
            except Exception:
                pass
        media = _vlc_sound_instance.media_new(path)
        _vlc_sound_player.set_media(media)
        _vlc_sound_player.audio_set_volume(volume)
        _vlc_sound_player.play()
    except Exception:
        if winsound:
            try:
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass


def _get_base_dir():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        if os.path.exists(os.path.join(exe_dir, 'resources')):
            return exe_dir
        if hasattr(sys, '_MEIPASS') and os.path.exists(os.path.join(sys._MEIPASS, 'resources')):
            return sys._MEIPASS
        return exe_dir
    return os.path.dirname(os.path.abspath(__file__))


def get_sounds_dir():
    """Retorna la ruta absoluta al directorio resources/sounds/."""
    path = os.path.join(_get_base_dir(), 'resources', 'sounds')
    os.makedirs(path, exist_ok=True)
    return path


def get_sound_file_path(sound_name='espera.wav'):
    """Retorna la ruta completa a un archivo de sonido en resources/sounds/."""
    sounds_dir = get_sounds_dir()
    return os.path.join(sounds_dir, sound_name)


def generate_subtle_waiting_wav(target_path=None):
    """
    Sintetiza un archivo WAV suave y cálido (tono armónico sutil con envolvente suave)
    ideal como sonido de espera periódico sin saturar ni molestar a lectores de pantalla.
    """
    if target_path is None:
        target_path = get_sound_file_path('espera.wav')

    sample_rate = 44100
    duration = 0.09  # 90 ms
    num_samples = int(sample_rate * duration)

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    with wave.open(target_path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        raw = []
        for i in range(num_samples):
            t = i / sample_rate
            # Envolvente suave: subida sinusoidal en 15ms y caída exponencial
            if t < 0.015:
                env = math.sin((t / 0.015) * (math.pi / 2))
            else:
                env = math.exp(-(t - 0.015) * 40.0)

            # Tono armónico suave: 523.25 Hz (Do5) con un armónico superior atenuado
            tone = (0.75 * math.sin(2 * math.pi * 523.25 * t) + 
                    0.25 * math.sin(2 * math.pi * 1046.50 * t))
            
            # Amplitud leve y cómoda (~16% de volumen máximo, aprox. -16dB)
            sample = int(tone * env * 32767 * 0.16)
            sample = max(-32768, min(32767, sample))
            raw.append(struct.pack('<h', sample))

        wav.writeframes(b''.join(raw))

    return target_path


def generate_completion_wav(target_path=None):
    """
    Sintetiza un archivo WAV brillante, potente y armonioso (doble tono ascendente Sol5 -> Do6)
    con volumen contundente (~75% de amplitud) para anunciar claramente el fin de todas las descargas.
    """
    if target_path is None:
        target_path = get_sound_file_path('completado.wav')

    sample_rate = 44100
    duration = 0.38  # 380 ms
    num_samples = int(sample_rate * duration)

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    with wave.open(target_path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        raw = []
        for i in range(num_samples):
            t = i / sample_rate
            sample_val = 0.0
            
            # Nota 1: Sol5 (783.99 Hz)
            if t < 0.16:
                t1 = t
                if t1 < 0.01:
                    env1 = math.sin((t1 / 0.01) * (math.pi / 2))
                else:
                    env1 = math.exp(-(t1 - 0.01) * 20.0)
                tone1 = 0.7 * math.sin(2 * math.pi * 783.99 * t1) + 0.3 * math.sin(2 * math.pi * 1567.98 * t1)
                sample_val += tone1 * env1
                
            # Nota 2: Do6 (1046.50 Hz) ascendente y resonante
            if t >= 0.11:
                t2 = t - 0.11
                if t2 < 0.012:
                    env2 = math.sin((t2 / 0.012) * (math.pi / 2))
                else:
                    env2 = math.exp(-(t2 - 0.012) * 12.0)
                tone2 = 0.75 * math.sin(2 * math.pi * 1046.50 * t2) + 0.25 * math.sin(2 * math.pi * 2093.00 * t2)
                sample_val += tone2 * env2
                
            # Amplitud enérgica y sonora (~75% de volumen máximo)
            sample = int(sample_val * 32767 * 0.75)
            sample = max(-32768, min(32767, sample))
            raw.append(struct.pack('<h', sample))

        wav.writeframes(b''.join(raw))

    return target_path


def ensure_sound_files():
    """Garantiza que los archivos de sonido existan en el sistema de archivos."""
    espera_path = get_sound_file_path('espera.wav')
    if not os.path.isfile(espera_path) or os.path.getsize(espera_path) < 100:
        try:
            generate_subtle_waiting_wav(espera_path)
        except Exception:
            pass
    comp_path = get_sound_file_path('completado.wav')
    if not os.path.isfile(comp_path) or os.path.getsize(comp_path) < 100:
        try:
            generate_completion_wav(comp_path)
        except Exception:
            pass
    return espera_path


def play_sound(sound_name='espera.wav', volume=90):
    """Reproduce de forma asíncrona y no bloqueante un sonido."""
    try:
        path = get_sound_file_path(sound_name)
        if not os.path.isfile(path):
            ensure_sound_files()
        if os.path.isfile(path):
            dev = get_audio_device()
            if dev:
                _play_vlc_sound_file(path, dev, volume=volume)
            elif winsound is not None:
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass


def play_completion_sound():
    """
    Reproduce con mayor volumen y nitidez el sonido de finalización de descargas.
    Detiene cualquier sonido de espera previo y emite el tono de completado.
    """
    stop_waiting_sound()
    try:
        ensure_sound_files()
        path = get_sound_file_path('completado.wav')
        dev = get_audio_device()
        if dev:
            _play_vlc_sound_file(path, dev, volume=100)
        elif winsound is not None:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        if winsound is not None:
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass


def is_waiting_sound_running():
    """Indica si el bucle de sonido de espera está actualmente activo."""
    with _lock:
        return _waiting_thread is not None and _waiting_thread.is_alive() and not _stop_event.is_set()


def _waiting_loop(interval):
    """Hilo trabajador que emite el sonido de espera a intervalos regulares."""
    ensure_sound_files()
    
    # Emitir el primer sonido inmediatamente al comenzar el proceso
    try:
        play_sound('espera.wav')
    except Exception:
        pass

    while not _stop_event.is_set():
        if _stop_event.wait(interval):
            break
        try:
            play_sound('espera.wav')
        except Exception:
            pass


def start_waiting_sound(interval=2.0):
    """
    Inicia la reproducción periódica del sonido de espera (cada 2 segundos por defecto).
    Es seguro llamarlo múltiples veces; si ya está corriendo, no crea hilos adicionales.
    """
    global _waiting_thread
    if winsound is None and not get_audio_device():
        return

    with _lock:
        if _waiting_thread is not None and _waiting_thread.is_alive() and not _stop_event.is_set():
            return  # Ya se encuentra en ejecución

        _stop_event.clear()
        _waiting_thread = threading.Thread(
            target=_waiting_loop, 
            args=(interval,), 
            name="WaitingSoundThread", 
            daemon=True
        )
        _waiting_thread.start()


def stop_waiting_sound():
    """
    Detiene inmediatamente el sonido de espera y purga cualquier sonido en reproducción.
    """
    global _waiting_thread, _vlc_sound_player
    with _lock:
        _stop_event.set()
        if winsound is not None:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        if _vlc_sound_player is not None:
            try:
                _vlc_sound_player.stop()
            except Exception:
                pass
        _waiting_thread = None
