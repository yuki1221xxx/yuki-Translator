"""Check GitHub Releases and apply installer-based updates."""
from __future__ import annotations

import json
import hashlib
import logging
import re
import subprocess
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from i18n import message, tr
from runtime import DATA_DIR, FROZEN
from version import APP_VERSION, GITHUB_OWNER, GITHUB_REPO, INSTALLER_PREFIX


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    url: str
    name: str
    sha256: str | None = None


def version_tuple(value: str) -> tuple[int, ...]:
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value.strip())
    return tuple(map(int, match.groups())) if match else (0, 0, 0)


def is_newer(candidate: str, current: str = APP_VERSION) -> bool:
    return version_tuple(candidate) > version_tuple(current)


def fetch_latest_release() -> dict | None:
    url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest'
    request = urllib.request.Request(
        url,
        headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': f'yuki-Translator/{APP_VERSION}',
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        logging.exception('Update check failed')
        return None


def find_installer_asset(release: dict) -> UpdateInfo | None:
    tag = str(release.get('tag_name', '')).lstrip('v')
    if not is_newer(tag):
        return None
    pattern = re.compile(rf'^{re.escape(INSTALLER_PREFIX)}-v{re.escape(tag)}\.exe$', re.I)
    for asset in release.get('assets', []):
        name = str(asset.get('name', ''))
        if pattern.match(name):
            url = str(asset.get('browser_download_url', ''))
            expected_prefix = f'https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/'
            if not url.startswith(expected_prefix):
                continue
            digest = str(asset.get('digest') or '')
            sha256 = digest.removeprefix('sha256:') if digest.startswith('sha256:') else None
            return UpdateInfo(version=tag, url=url, name=name, sha256=sha256)
    return None


def check_for_update() -> UpdateInfo | None:
    release = fetch_latest_release()
    if not release:
        return None
    return find_installer_asset(release)


def download_update(info: UpdateInfo, report=lambda _msg: None) -> Path:
    target = DATA_DIR / 'updates' / info.name
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + '.partial')
    if partial.exists():
        partial.unlink()
    request = urllib.request.Request(
        info.url,
        headers={'User-Agent': f'yuki-Translator/{APP_VERSION}'},
    )
    report(message('update_downloading', version=info.version))
    with urllib.request.urlopen(request, timeout=60) as response:
        total = int(response.headers.get('Content-Length', 0))
        read = 0
        chunk_size = 1024 * 256
        with partial.open('wb') as handle:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                handle.write(chunk)
                read += len(chunk)
                if total:
                    percent = min(100, int(read * 100 / total))
                    report(message('update_download_progress', version=info.version, percent=percent))
    if info.sha256:
        actual = hashlib.sha256(partial.read_bytes()).hexdigest()
        if actual.lower() != info.sha256.lower():
            partial.unlink(missing_ok=True)
            raise ValueError('Downloaded update checksum does not match GitHub Release')
    if target.exists():
        target.unlink()
    partial.replace(target)
    return target


def apply_update(installer_path: Path) -> None:
    subprocess.Popen(
        [
            str(installer_path),
            '/VERYSILENT',
            '/SUPPRESSMSGBOXES',
            '/NORESTARTAPPLICATIONS',
            '/CLOSEAPPLICATIONS',
            '/UPDATE',
        ],
        close_fds=True,
    )
    raise SystemExit(0)


def prompt_and_apply(root, installer_path: Path, language: str) -> None:
    from tkinter import messagebox

    if messagebox.askyesno(
        tr('update_ready_title', language),
        tr('update_ready_body', language, version=installer_path.stem.split('-v')[-1]),
        parent=root,
    ):
        apply_update(installer_path)


class UpdateManager:
    def __init__(self, app):
        self.app = app
        self._running = False

    def start(self):
        if not FROZEN or self._running:
            return
        self._running = True
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        try:
            info = check_for_update()
            if not info:
                return
            installer = download_update(info, lambda msg: self.app.events.put(('status', msg)))
            self.app.events.put(('update_ready', installer))
        except Exception as exc:
            logging.exception('Automatic update failed')
            self.app.events.put(('notice', message('update_failed', detail=exc)))
