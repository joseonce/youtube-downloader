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
            if folder == 'resources':
                # No copiar la carpeta obsoleta vlc ni duplicados de libmpv
                shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns('vlc', 'libmpv-2.dll'))
            else:
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

    print("Comprimiendo en YouTubeDownloader.zip (sin yt-dlp, incluyendo bin, docs, resources)...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dist_dir):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, dist_dir)
                parts = rel_path.split(os.sep)
                # Excluir la carpeta config del paquete comprimido para no sobreescribir datos del usuario
                if 'config' in parts:
                    continue
                # Excluir la carpeta obsoleta vlc (migrado a libmpv)
                if 'vlc' in parts:
                    continue
                # Excluir binario de yt-dlp para mantener el paquete ligero (se descarga automáticamente al inicio si falta)
                if f.lower().startswith('yt-dlp'):
                    continue
                # Excluir duplicados redundantes de la biblioteca mpv
                if f.lower() == 'libmpv-2.dll':
                    continue
                arc_name = os.path.join('YouTubeDownloader', rel_path)
                zf.write(full_path, arc_name)

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"Paquete generado exitosamente: YouTubeDownloader.zip ({size_mb:.2f} MB)")

if __name__ == '__main__':
    main()
