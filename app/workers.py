from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app.crawler import CrawlCancelled, DirectoryCrawler
from app.downloader import DownloadCancelled, FileDownloader
from app.models import DownloadTask


class DownloadManagerWorker(QObject):
    item_progress = Signal(int, int)
    item_status = Signal(int, str)
    item_size = Signal(int, object)
    tasks_ready = Signal(list)
    stats = Signal(object)
    log = Signal(str)
    error = Signal(str)
    finished = Signal()

    def __init__(self, base_url: str, tasks: list[DownloadTask], save_dir: str, run_mode: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.tasks = tasks
        self.save_root = Path(save_dir) if save_dir else Path(".")
        self.run_mode = run_mode
        self._cancelled = False
        self.crawler = DirectoryCrawler()
        self.downloader = FileDownloader()
        self._downloaded_bytes = 0
        self._start_time = 0.0
        self._last_emit = 0.0

    def cancel(self) -> None:
        self._cancelled = True

    def _should_cancel(self) -> bool:
        return self._cancelled

    def _emit_stats(self, phase: str, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_emit < 0.2:
            return
        self._last_emit = now
        total_known = sum(task.size or 0 for task in self.tasks)
        unknown_count = sum(1 for task in self.tasks if task.size is None)
        elapsed = max(0.0, now - self._start_time) if self._start_time else 0.0
        speed = (self._downloaded_bytes / elapsed) if elapsed > 0 else 0.0
        eta = None
        if unknown_count == 0 and speed > 0 and total_known >= self._downloaded_bytes:
            eta = int((total_known - self._downloaded_bytes) / speed)

        self.stats.emit(
            {
                "phase": phase,
                "file_count": len(self.tasks),
                "known_total_bytes": total_known,
                "unknown_files": unknown_count,
                "downloaded_bytes": self._downloaded_bytes,
                "speed_bps": speed,
                "elapsed_seconds": int(elapsed),
                "eta_seconds": eta,
            }
        )

    def _on_chunk(self, chunk_len: int) -> None:
        self._downloaded_bytes += chunk_len
        self._emit_stats("下载中")

    @Slot()
    def run(self) -> None:
        phase = "待命"
        try:
            if self.run_mode in ("scan_only", "scan_then_download"):
                phase = "扫描中"
                result = self.crawler.crawl(self.base_url, self._should_cancel, self.log.emit)
                self.tasks = [
                    DownloadTask(index=i + 1, relative_path=item["relative_path"], file_url=item["url"], size=item.get("size"))
                    for i, item in enumerate(result)
                ]
                self.tasks_ready.emit(self.tasks)
                self._emit_stats("扫描中", force=True)

            if self._should_cancel():
                self.log.emit("任务已取消: 用户在扫描阶段取消")
                self._emit_stats("已取消", force=True)
                return

            if self.run_mode in ("download_only", "scan_then_download"):
                phase = "下载中"
                self._start_time = time.time()
                self._emit_stats("下载中", force=True)
                for task in self.tasks:
                    if self._should_cancel():
                        self.log.emit("任务已取消: 用户在下载阶段取消")
                        self.item_status.emit(task.index, "已取消")
                        self._emit_stats("已取消", force=True)
                        return
                    self.item_status.emit(task.index, "下载中")
                    status, _bytes = self.downloader.download(
                        task=task,
                        root_dir=self.save_root,
                        should_cancel=self._should_cancel,
                        progress_callback=self.item_progress.emit,
                        size_callback=self.item_size.emit,
                        bytes_callback=self._on_chunk,
                        log_callback=self.log.emit,
                    )
                    self.item_status.emit(task.index, status)
                    self._emit_stats("下载中", force=True)

            self._emit_stats("已完成", force=True)
        except CrawlCancelled as exc:
            self.log.emit(str(exc))
            self._emit_stats("已取消", force=True)
        except DownloadCancelled as exc:
            self.log.emit(str(exc))
            self._emit_stats("已取消", force=True)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"{phase}失败: {exc}")
            self._emit_stats("失败", force=True)
        finally:
            self.finished.emit()
