from __future__ import annotations

from pathlib import Path

import requests

from app.models import DownloadTask


class DownloadCancelled(Exception):
    pass


class FileDownloader:
    def __init__(self, timeout: tuple[int, int] = (8, 30), chunk_size: int = 1024 * 128) -> None:
        self.timeout = timeout
        self.chunk_size = chunk_size

    def download(
        self,
        task: DownloadTask,
        root_dir: Path,
        should_cancel,
        progress_callback,
        size_callback,
        log_callback,
    ) -> str:
        if should_cancel():
            raise DownloadCancelled("下载已取消")

        final_path = task.local_path(root_dir)
        final_path.parent.mkdir(parents=True, exist_ok=True)

        if final_path.exists() and task.size is not None and final_path.stat().st_size == task.size:
            progress_callback(task.index, 100)
            log_callback(f"跳过(大小一致): {task.relative_path}")
            return "已跳过"

        temp_path = final_path.with_suffix(final_path.suffix + ".part")
        if temp_path.exists():
            temp_path.unlink()

        log_callback(f"下载: {task.file_url}")
        try:
            with requests.get(task.file_url, stream=True, timeout=self.timeout) as response:
                response.raise_for_status()
                total = int(response.headers.get("Content-Length", "0") or 0)
                if total > 0:
                    task.size = total
                    size_callback(task.index, task.size)
                downloaded = 0

                with temp_path.open("wb") as file_handle:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if should_cancel():
                            raise DownloadCancelled("下载已取消")
                        if not chunk:
                            continue
                        file_handle.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            progress = int(downloaded * 100 / total)
                            progress_callback(task.index, min(100, progress))
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

        temp_path.replace(final_path)
        progress_callback(task.index, 100)
        return "已完成"
