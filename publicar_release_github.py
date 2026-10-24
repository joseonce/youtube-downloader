"""
Script para crear Release en GitHub y subir YouTubeDownloader.zip automáticamente.
"""
import os
import sys
import json
import urllib.request
import urllib.error

def get_token():
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        return token.strip()
    
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('GITHUB_TOKEN='):
                    return line.split('=', 1)[1].strip()
    return None

def main():
    token = get_token()
    if not token:
        print("[ERROR] No se encontro el token de GitHub (GITHUB_TOKEN en .env)")
        sys.exit(1)
        
    repo_owner = "joseonce"
    repo_name = "youtube-downloader"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Verificar autenticacion
    print(f"Probando conexion con GitHub API para {repo_owner}/{repo_name}...")
    user_req = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ReleaseUploader/1.0"
        }
    )
    try:
        with urllib.request.urlopen(user_req) as resp:
            user_data = json.loads(resp.read().decode('utf-8'))
            print(f"[OK] Autenticado como: {user_data.get('login')} ({user_data.get('name')})")
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Fallo la autenticacion con el token: HTTP {e.code} - {e.reason}")
        sys.exit(1)

    # 2. Leer version.json
    version_file = os.path.join(base_dir, 'version.json')
    if not os.path.exists(version_file):
        print("[ERROR] No existe version.json")
        sys.exit(1)
        
    with open(version_file, 'r', encoding='utf-8') as f:
        ver_info = json.load(f)
        
    version_str = ver_info.get('version', '1.0.0')
    tag_name = f"v{version_str}"
    release_name = f"Descargador de YouTube {tag_name}"
    
    # Changelog de la version
    changelog_lines = ver_info.get('changelog', [])
    relevant_notes = [line for line in changelog_lines if version_str in line]
    if not relevant_notes:
        relevant_notes = changelog_lines[:10]
    body_text = "\n".join(f"- {n}" for n in relevant_notes)
    
    # 3. Comprobar o crear Release
    print(f"Comprobando Release para el tag {tag_name}...")
    release_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/tags/{tag_name}"
    req_rel = urllib.request.Request(
        release_api_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ReleaseUploader/1.0"
        }
    )
    release_data = None
    try:
        with urllib.request.urlopen(req_rel) as resp:
            release_data = json.loads(resp.read().decode('utf-8'))
            print(f"[INFO] Release existente encontrada: {release_data.get('name')} (ID: {release_data.get('id')})")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"Creando nueva Release {tag_name} en GitHub...")
            create_payload = json.dumps({
                "tag_name": tag_name,
                "target_commitish": "main",
                "name": release_name,
                "body": body_text,
                "draft": False,
                "prerelease": False
            }).encode('utf-8')
            
            req_create = urllib.request.Request(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases",
                data=create_payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json",
                    "User-Agent": "ReleaseUploader/1.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req_create) as resp:
                release_data = json.loads(resp.read().decode('utf-8'))
                print(f"[OK] Release creada exitosamente: {release_data.get('html_url')}")
        else:
            raise

    # 4. Subir YouTubeDownloader.zip
    zip_path = os.path.join(base_dir, 'YouTubeDownloader.zip')
    if not os.path.exists(zip_path):
        print(f"[ERROR] No se encontro {zip_path}")
        sys.exit(1)
        
    zip_size = os.path.getsize(zip_path)
    zip_size_mb = zip_size / (1024 * 1024)
    file_name = 'YouTubeDownloader.zip'
    
    # Comprobar si ya existe el asset
    assets = release_data.get('assets', [])
    for asset in assets:
        if asset.get('name') == file_name:
            print(f"Eliminando asset existente anterior {file_name} (ID: {asset['id']})...")
            del_req = urllib.request.Request(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/assets/{asset['id']}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "ReleaseUploader/1.0"
                },
                method="DELETE"
            )
            with urllib.request.urlopen(del_req) as resp:
                pass
            print("[OK] Asset anterior eliminado.")
            break
            
    print(f"Subiendo {file_name} ({zip_size_mb:.2f} MB) a GitHub Releases...")
    upload_url_template = release_data.get('upload_url', '')
    upload_url = upload_url_template.split('{')[0] + f"?name={file_name}"
    
    with open(zip_path, 'rb') as zf:
        data = zf.read()
        
    req_upload = urllib.request.Request(
        upload_url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/zip",
            "Content-Length": str(zip_size),
            "User-Agent": "ReleaseUploader/1.0"
        },
        method="POST"
    )
    
    with urllib.request.urlopen(req_upload) as resp:
        asset_res = json.loads(resp.read().decode('utf-8'))
        download_url = asset_res.get('browser_download_url')
        print(f"[EXITO] Paquete subido correctamente!")
        print(f"URL de descarga: {download_url}")
        print(f"Pagina de Release: {release_data.get('html_url')}")

if __name__ == '__main__':
    main()
