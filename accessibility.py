"""
Módulo de Accesibilidad para la aplicación de YouTube.
Permite enviar anuncios hablados y en braille a lectores de pantalla
como NVDA, JAWS, Narrador de Windows o System Speech sin alterar el foco.

Solo emite locuciones si la aplicación tiene el foco y si se detecta
un lector de pantalla activo (evitando locuciones innecesarias para usuarios
videntes o sin lector), salvo configuración explícita del usuario.
"""

import os
import sys

_speaker = None
_initialized = False
_modo_locuciones = 'auto'  # 'auto' (solo lector activo), 'siempre', 'desactivado'


def set_modo_locuciones(modo: str):
    """Establece el modo de locuciones: 'auto', 'siempre' o 'desactivado'."""
    global _modo_locuciones
    if modo in ('auto', 'siempre', 'desactivado'):
        _modo_locuciones = modo
    elif modo is False:
        _modo_locuciones = 'desactivado'
    elif modo is True:
        _modo_locuciones = 'siempre'
    else:
        _modo_locuciones = 'auto'


def get_modo_locuciones() -> str:
    """Retorna el modo configurado para las locuciones."""
    global _modo_locuciones
    return _modo_locuciones


def is_screen_reader_active() -> bool:
    """
    Retorna True si hay un lector de pantalla real en ejecución (NVDA, JAWS, Dolphin, Narrador, etc.).
    Retorna False si solo está disponible la síntesis genérica del sistema SAPI5 pero ningún lector activo,
    evitando hablar a personas videntes que no necesitan asistencia de voz.
    """
    # 1. Comprobar lectores a través de accessible_output2 (excluyendo SAPI/eSpeak genéricos)
    try:
        global _speaker, _initialized
        if not _initialized:
            init_accessibility()
        if _speaker and hasattr(_speaker, 'outputs'):
            for out in _speaker.outputs:
                name = getattr(out, 'name', '').lower()
                if name not in ('sapi5', 'sapi4', 'e_speak', 'espeak'):
                    try:
                        if out.is_active():
                            return True
                    except Exception:
                        pass
    except Exception:
        pass

    # 2. Comprobar Narrador de Windows (Windows Narrator)
    if sys.platform.startswith('win'):
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            # Ventanas del Narrador
            if user32.FindWindowW("NarratorHelperWindow", None) != 0:
                return True
            if user32.FindWindowW("StandardWindow_Narrator", None) != 0:
                return True
            if user32.FindWindowW(None, "Narrator") != 0 or user32.FindWindowW(None, "Narrador") != 0:
                return True

            # Proceso Narrator.exe
            kernel32 = ctypes.windll.kernel32
            TH32CS_SNAPPROCESS = 0x00000002
            h_snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if h_snap != -1:
                class PROCESSENTRY32W(ctypes.Structure):
                    _fields_ = [
                        ("dwSize", wintypes.DWORD),
                        ("cntUsage", wintypes.DWORD),
                        ("th32ProcessID", wintypes.DWORD),
                        ("th32DefaultHeapID", ctypes.c_size_t),
                        ("th32ModuleID", wintypes.DWORD),
                        ("cntThreads", wintypes.DWORD),
                        ("th32ParentProcessID", wintypes.DWORD),
                        ("pcPriClassBase", ctypes.c_long),
                        ("dwFlags", wintypes.DWORD),
                        ("szExeFile", ctypes.c_wchar * 260),
                    ]
                pe = PROCESSENTRY32W()
                pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
                success = kernel32.Process32FirstW(h_snap, ctypes.byref(pe))
                found = False
                while success:
                    if pe.szExeFile.lower() == "narrator.exe":
                        found = True
                        break
                    success = kernel32.Process32NextW(h_snap, ctypes.byref(pe))
                kernel32.CloseHandle(h_snap)
                if found:
                    return True
        except Exception:
            pass

    return False


def is_app_active() -> bool:
    """
    Determina si la aplicación tiene el foco activo en el sistema operativo.
    Retorna True si alguna ventana de este proceso tiene el foco en primer plano,
    o False si el usuario está trabajando en otra aplicación (Word, navegador, etc.).
    """
    if sys.platform.startswith('win'):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            fg_hwnd = user32.GetForegroundWindow()
            if fg_hwnd:
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(pid))
                return pid.value == os.getpid()
        except Exception:
            pass

    try:
        import wx
        app = wx.GetApp()
        if app and hasattr(app, 'IsActive'):
            return bool(app.IsActive())
    except Exception:
        pass

    return True


def init_accessibility():
    global _speaker, _initialized
    if _initialized:
        return _speaker
    try:
        import accessible_output2.outputs.auto
        _speaker = accessible_output2.outputs.auto.Auto()
    except Exception:
        _speaker = None
    _initialized = True
    return _speaker


def speak(message: str, interrupt: bool = True, require_focus: bool = True):
    """
    Anuncia un mensaje al lector de pantalla activo.
    
    Reglas de locución:
    1. Si 'modo_locuciones' es 'desactivado', no se emite ninguna locución.
    2. Si 'modo_locuciones' es 'auto' (predeterminado), solo emite si se detecta un lector
       de pantalla real activo (NVDA, JAWS, Narrador, etc.). Si no hay lector activo (personas videntes),
       no emite locución para no molestar.
    3. Si 'modo_locuciones' es 'siempre', emite locución (usando lector o SAPI5 si no hay lector).
    4. Salvo que require_focus=False, solo emite si la aplicación tiene el foco activo en Windows.
    """
    if not message:
        return

    global _modo_locuciones
    if _modo_locuciones == 'desactivado':
        return

    if _modo_locuciones == 'auto':
        if not is_screen_reader_active():
            return

    if require_focus and not is_app_active():
        return

    global _speaker, _initialized
    if not _initialized and _speaker is None:
        init_accessibility()
    if _speaker:
        try:
            _speaker.speak(str(message), interrupt=interrupt)
        except Exception:
            pass


def shutdown_accessibility():
    """
    Libera los recursos y referencias del subsistema de accesibilidad,
    incluyendo referencias COM a JAWS/SAPI para evitar bloqueos en memoria.
    """
    global _speaker, _initialized
    if _speaker is not None:
        try:
            outputs = getattr(_speaker, 'outputs', [])
            for out in outputs:
                # Liberar objeto COM subyacente (JAWS, SAPI5, etc.) si existe
                obj = getattr(out, 'object', None)
                if obj is not None:
                    try:
                        del obj
                    except Exception:
                        pass
                    try:
                        setattr(out, 'object', None)
                    except Exception:
                        pass
        except Exception:
            pass
    _speaker = None
    _initialized = False
