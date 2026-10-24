"""Pruebas reales del relevo PowerShell sobre instalaciones desechables."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
import zipfile
from update_transaction import UPDATE_SCRIPT

OLD_APP = "from pathlib import Path\nPath('old-started').write_text('ok')\n"
NEW_APP = "import os\nfrom pathlib import Path\nPath(os.environ['YT_UPDATE_READY']).write_text('ready')\n"

class TransactionTests(unittest.TestCase):
    def run_case(self, mode):
        with tempfile.TemporaryDirectory(prefix='yt prueba á ') as root:
            root = Path(root)
            target = root / 'Aplicación usuario'
            work = root / 'work'
            target.mkdir(); work.mkdir()
            (target / 'app.py').write_text(OLD_APP)
            (target / 'config').mkdir()
            (target / 'config' / 'personal.json').write_text('mis preferencias')
            (target / 'personal.txt').write_text('archivo del usuario')
            package = work / 'package.zip'
            if mode == 'invalid_zip':
                package.write_bytes(b'invalid')
            else:
                with zipfile.ZipFile(package, 'w') as archive:
                    archive.writestr('YouTubeDownloader/app.py', 'raise RuntimeError("bad start")' if mode == 'bad_start' else 'import time; time.sleep(20)' if mode == 'no_ready' else NEW_APP)
                    archive.writestr('YouTubeDownloader/new.txt', 'nuevo')
                    archive.writestr('YouTubeDownloader/config/personal.json', 'no sobrescribir')
            script = UPDATE_SCRIPT
            # Evitar dialogos interactivos durante las pruebas.
            script = '\n'.join(line for line in script.splitlines() if '$shell.Popup(' not in line)
            if mode == 'copy_failure':
                script = script.replace('Copy-Tree $source $stage $true', 'throw "fallo de copia simulado"')
            if mode == 'verification_failure':
                script = script.replace('    Copy-Tree $source $stage $true', '    Copy-Tree $source $stage $true\n    [IO.File]::WriteAllText((Join-Path $stage $c.entry), "corrupto")')
            if mode == 'no_ready':
                script = script.replace('.AddSeconds(60)', '.AddSeconds(1)')
            if mode == 'swap_failure':
                script = script.replace('Move-Owned $stage $target', 'throw "fallo de intercambio simulado"')
            script_path = work / 'install.ps1'
            script_path.write_text(script, encoding='utf-8-sig')
            settings = work / 'settings.json'
            settings.write_text(json.dumps(dict(target=str(target),work=str(work),zip=str(package),token=uuid.uuid4().hex,pid=2147483647,entry='app.py',python=sys.executable)),encoding='utf-8')
            result = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script_path),'-Settings',str(settings)],capture_output=True,timeout=45)
            import time
            time.sleep(.3)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            self.assertFalse(work.exists(), 'quedaron temporales')
            self.assertEqual(sorted(p.name for p in root.iterdir()),[target.name])
            self.assertEqual((target/'config'/'personal.json').read_text(),'mis preferencias')
            self.assertEqual((target/'personal.txt').read_text(),'archivo del usuario')
            if mode == 'success':
                self.assertEqual((target/'app.py').read_text(),NEW_APP)
                self.assertTrue((target/'new.txt').exists())
            else:
                self.assertEqual((target/'app.py').read_text(),OLD_APP)
                self.assertFalse((target/'new.txt').exists())
                # Dar tiempo al proceso restaurado para escribir su marca.
                import time
                for _ in range(100):
                    if (target/'old-started').exists(): break
                    time.sleep(.05)
                self.assertTrue((target/'old-started').exists())

    def test_success(self): self.run_case('success')
    def test_invalid_zip(self): self.run_case('invalid_zip')
    def test_copy_failure(self): self.run_case('copy_failure')
    def test_swap_failure(self): self.run_case('swap_failure')
    def test_verification_failure(self): self.run_case('verification_failure')
    def test_no_ready(self): self.run_case('no_ready')
    def test_bad_start(self): self.run_case('bad_start')

if __name__ == '__main__': unittest.main()
