import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import tempfile

CURRENT_VERSION = "1.0.0"
REPO_OWNER = "krrishramsaran"
REPO_NAME = "omnitool"
API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

def parse_version(ver_str: str) -> tuple:
    '''Convert v1.2.3 into (1, 2, 3) for numerical comparison.'''
    clean = ver_str.strip().lstrip('v').lstrip('V')
    parts = []
    for p in clean.split('.'):
        if p.isdigit():
            parts.append(int(p))
    return tuple(parts)

def check_for_updates(github_token: str = None) -> dict:
    '''
    Checks GitHub releases for a newer version.
    Returns: {
        'has_update': bool,
        'current_version': str,
        'latest_version': str,
        'download_url': str or None,
        'release_notes': str
    }
    '''
    req = urllib.request.Request(API_URL)
    req.add_header('User-Agent', 'OmniTool-Desktop-App')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    if github_token:
        req.add_header('Authorization', f'token {github_token}')

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            tag = data.get('tag_name', '')
            latest_v = parse_version(tag)
            curr_v = parse_version(CURRENT_VERSION)

            has_update = latest_v > curr_v

            # Find matching Windows asset
            download_url = None
            for asset in data.get('assets', []):
                name = asset.get('name', '').lower()
                if 'windows' in name and name.endswith('.zip'):
                    download_url = asset.get('browser_download_url')
                    break

            return {
                'has_update': has_update,
                'current_version': CURRENT_VERSION,
                'latest_version': tag,
                'download_url': download_url,
                'release_notes': data.get('body', '')
            }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {'error': 'Repository or release not found. (If private, authentication is required).', 'has_update': False}
        return {'error': f'HTTP Error {e.code}', 'has_update': False}
    except Exception as e:
        return {'error': str(e), 'has_update': False}

def download_and_install_update(download_url: str, progress_callback=None):
    '''
    Downloads update zip to temp folder and executes apply_update script.
    '''
    temp_dir = tempfile.gettempdir()
    zip_path = os.path.join(temp_dir, 'OmniTool_Update.zip')

    req = urllib.request.Request(download_url)
    req.add_header('User-Agent', 'OmniTool-Desktop-App')

    with urllib.request.urlopen(req) as resp:
        total_size = int(resp.headers.get('Content-Length', 0))
        downloaded = 0
        chunk_size = 1024 * 64

        with open(zip_path, 'wb') as out_f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out_f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total_size > 0:
                    pct = downloaded / total_size
                    progress_callback(pct)

    # Determine destination directory
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
        exe_name = os.path.basename(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        exe_name = 'main.py'

    # Create updater script
    updater_bat = os.path.join(temp_dir, 'apply_omnitool_update.bat')
    bat_content = f'''@echo off
timeout /t 2 /nobreak >nul
echo Applying OmniTool update...
tar -xf "{zip_path}" -C "{app_dir}"
if exist "{app_dir}\\{exe_name}" (
    start "" "{app_dir}\\{exe_name}"
) else (
    start "" "{app_dir}\\OmniTool.exe"
)
del "{zip_path}" >nul 2>&1
del "%~f0" >nul 2>&1
'''
    with open(updater_bat, 'w', encoding='utf-8') as f:
        f.write(bat_content)

    # Launch updater detached and exit current process
    subprocess.Popen(
        ['cmd.exe', '/c', updater_bat],
        creationflags=subprocess.DETACHED_PROCESS if os.name == 'nt' else 0,
        close_fds=True
    )
    sys.exit(0)
