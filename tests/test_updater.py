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

def test_updater_module():
    print("\n[8/8] Probando módulo de actualización automática (updater.py)...")
    import json
    import updater
    assert updater.APP_VERSION == "1.6.3"
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
    assert updater.parse_version("1.6.0") == (1, 6, 0)
    assert updater.parse_version("2.0") == (2, 0)
    assert updater.parse_version("1.6.0") > updater.parse_version("1.5.9")
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
        assert data["version"] == "1.6.3", "version.json debe tener la versión 1.6.3"
        assert "url" in data, "version.json debe contener el campo url"
        assert "changelog" in data, "version.json debe contener el campo changelog"

    print("  -> Módulo updater, parseo SemVer y version.json validados correctamente.")


if __name__ == '__main__':
    test_updater_module()
    print("\n[OK] Todas las pruebas de test_updater.py pasaron satisfactoriamente.")
