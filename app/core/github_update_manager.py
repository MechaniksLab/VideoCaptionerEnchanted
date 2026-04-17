import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests

from app.common.config import cfg
from app.config import CACHE_PATH, ROOT_PATH, UPDATE_REPO_BRANCH, UPDATE_REPO_NAME, UPDATE_REPO_OWNER


class GitHubUpdateManager:
    """Проверка и применение обновлений из GitHub-репозитория."""

    def __init__(self):
        self.app_root = ROOT_PATH.parent
        self.updater_root = CACHE_PATH / "updater"
        self.updater_root.mkdir(parents=True, exist_ok=True)

    def _repo(self):
        # Репозиторий фиксирован внутри приложения (без UI-настроек)
        return UPDATE_REPO_OWNER, UPDATE_REPO_NAME, UPDATE_REPO_BRANCH

    def fetch_latest_commit(self) -> Dict:
        owner, name, branch = self._repo()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ShortsCreatorStudio-Updater",
        }

        def _parse_commit(data: Dict, used_branch: str) -> Dict:
            return {
                "sha": str(data.get("sha") or "").strip(),
                "html_url": str(data.get("html_url") or "").strip(),
                "message": str(((data.get("commit") or {}).get("message") or "")).strip(),
                "branch": used_branch,
            }

        # 1) Пробуем ветку из конфига
        primary_url = f"https://api.github.com/repos/{owner}/{name}/commits/{branch}"
        r = requests.get(primary_url, timeout=15, headers=headers)
        if r.ok:
            return _parse_commit(r.json() or {}, branch)

        # 2) Если ref некорректен (часто 422), берем default_branch репозитория
        repo_url = f"https://api.github.com/repos/{owner}/{name}"
        rr = requests.get(repo_url, timeout=15, headers=headers)
        rr.raise_for_status()
        repo_info = rr.json() or {}
        default_branch = str(repo_info.get("default_branch") or branch).strip() or branch

        fallback_url = f"https://api.github.com/repos/{owner}/{name}/commits/{default_branch}"
        rf = requests.get(fallback_url, timeout=15, headers=headers)
        if rf.ok:
            return _parse_commit(rf.json() or {}, default_branch)

        # 3) Последний резерв: самый свежий коммит из списка
        list_url = f"https://api.github.com/repos/{owner}/{name}/commits?per_page=1"
        rl = requests.get(list_url, timeout=15, headers=headers)
        rl.raise_for_status()
        items = rl.json() or []
        if not items:
            raise requests.HTTPError("GitHub API returned no commits")
        data = items[0] or {}
        return {
            "sha": str(data.get("sha") or "").strip(),
            "html_url": str(data.get("html_url") or "").strip(),
            "message": str(((data.get("commit") or {}).get("message") or "")).strip(),
            "branch": default_branch,
        }

    def check_update(self) -> Dict:
        latest = self.fetch_latest_commit()
        latest_sha = latest.get("sha", "")
        known_sha = str(cfg.update_last_known_commit.value or "").strip()

        # Первый запуск: фиксируем baseline без навязчивого апдейта.
        if not known_sha and latest_sha:
            cfg.set(cfg.update_last_known_commit, latest_sha)
            return {"has_update": False, "latest": latest, "known": latest_sha, "baseline_initialized": True}

        return {
            "has_update": bool(latest_sha and known_sha and latest_sha != known_sha),
            "latest": latest,
            "known": known_sha,
            "baseline_initialized": False,
        }

    def apply_update_and_restart(self) -> Dict:
        latest = self.fetch_latest_commit()
        sha = latest.get("sha", "")
        if not sha:
            return {"ok": False, "error": "Не удалось получить SHA последнего коммита"}

        owner, name, _ = self._repo()
        # Скачиваем по SHA коммита, чтобы не зависеть от названия ветки
        zip_url = f"https://api.github.com/repos/{owner}/{name}/zipball/{sha}"

        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        stage_dir = self.updater_root / f"stage_{stamp}"
        extract_dir = stage_dir / "extract"
        stage_dir.mkdir(parents=True, exist_ok=True)
        extract_dir.mkdir(parents=True, exist_ok=True)
        zip_path = stage_dir / "update.zip"

        with requests.get(zip_url, timeout=45, stream=True) as r:
            r.raise_for_status()
            with zip_path.open("wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        children = [p for p in extract_dir.iterdir() if p.is_dir()]
        if not children:
            return {"ok": False, "error": "Архив обновления пуст"}
        src_root = children[0]

        launcher = self._resolve_launcher()
        script_path = stage_dir / "apply_update.bat"
        script = self._build_update_script(src_root=src_root, dst_root=self.app_root, launcher=launcher)
        script_path.write_text(script, encoding="utf-8")

        subprocess.Popen(
            ["cmd", "/c", str(script_path)],
            creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP") else 0),
        )

        return {"ok": True, "sha": sha, "script": str(script_path)}

    def _resolve_launcher(self) -> str:
        # В режиме exe
        if getattr(sys, "frozen", False):
            return f'"{Path(sys.executable)}"'

        # В режиме разработки пробуем запускать текущий python + main.py (если есть)
        py = str(Path(sys.executable))
        for candidate in [self.app_root / "main.py", self.app_root / "run.py"]:
            if candidate.exists():
                return f'"{py}" "{candidate}"'

        # fallback: просто текущий python
        return f'"{py}"'

    @staticmethod
    def _build_update_script(src_root: Path, dst_root: Path, launcher: str) -> str:
        src = str(src_root)
        dst = str(dst_root)
        # /XD исключаем runtime и пользовательские данные.
        return (
            "@echo off\n"
            "chcp 65001 >nul\n"
            "setlocal\n"
            f"set SRC={src}\n"
            f"set DST={dst}\n"
            "timeout /t 4 /nobreak >nul\n"
            "robocopy \"%SRC%\" \"%DST%\" /E /R:2 /W:1 /XD \"%DST%\\runtime\" \"%DST%\\AppData\" \"%DST%\\work-dir\" >nul\n"
            "set RC=%ERRORLEVEL%\n"
            "if %RC% GEQ 8 goto :end\n"
            f"start \"\" {launcher}\n"
            ":end\n"
            "endlocal\n"
        )
