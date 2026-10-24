"""
Script auxiliar para sincronizar directorios en dist/ y crear YouTubeDownloader.zip.
"""
import os
import shutil
import zipfile

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, 'dist')

    for folder in ['bin', 'docs', 'resources']:
        src = os.path.join(base_dir, folder)
        dst = os.path.join(dist_dir, folder)
        if os.path.exists(src):
            os.makedirs(dst, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print(f"Sincronizado: {folder} -> dist/{folder}")

    for file_name in ['ultimos_cambios.txt', 'CHANGELOG.md', 'version.json']:
        src_file = os.path.join(base_dir, file_name)
        if os.path.exists(src_file):
            shutil.copy2(src_file, os.path.join(dist_dir, file_name))
            print(f"Sincronizado: {file_name} -> dist/{file_name}")

    zip_path = os.path.join(base_dir, 'YouTubeDownloader.zip')
    if os.path.exists(zip_path):
        os.remove(zip_path)

    print("Comprimiendo en YouTubeDownloader.zip (incluyendo bin [sin yt-dlp], docs, resources)...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dist_dir):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, dist_dir)
                parts = rel_path.split(os.sep)
                # Excluir la carpeta config del paquete comprimido para no sobreescribir datos del usuario
                if 'config' in parts:
                    continue
                # Excluir yt-dlp para que la app solicite descargar siempre la versión más reciente al usuario
                if f.lower().startswith('yt-dlp'):
                    continue
                arc_name = os.path.join('YouTubeDownloader', rel_path)
                zf.write(full_path, arc_name)

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"Paquete generado exitosamente: YouTubeDownloader.zip ({size_mb:.2f} MB)")

if __name__ == '__main__':
    main()
