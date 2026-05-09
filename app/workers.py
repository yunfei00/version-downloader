from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app.crawler import CrawlCancelled, DirectoryCrawler
from app.downloader import DownloadCancelled, FileDownloader
from app.models import DownloadTask


class ScanWorker(QObject):
    finished = Signal(list)
    log = Signal(str)
    error = Signal(str)

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self._cancelled = False
        self.crawler = DirectoryCrawler()

    def cancel(self) -> None:
        self._cancelled = True

    def _should_cancel(self) -> bool:
        return self._cancelled

    @Slot()
    def run(self) -> None:
        try:
            result = self.crawler.crawl(self.base_url, self._should_cancel, self.log.emit)
            tasks = [
                DownloadTask(index=i + 1, relative_path=item["relative_path"], file_url=item["url"], size=item.get("size"))
                for i, item in enumerate(result)
            ]
            self.finished.emit(tasks)
        except CrawlCancelled as exc:
            self.log.emit(str(exc))
            self.finished.emit([])
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"扫描失败: {exc}")
            self.finished.emit([])


class DownloadWorker(QObject):
    item_progress = Signal(int, int)
    item_status = Signal(int, str)
    item_size = Signal(int, object)
    log = Signal(str)
    summary = Signal(int, int, int, int)
    finished = Signal()
    error = Signal(str)

    def __init__(self, tasks: list[DownloadTask], save_dir: str) -> None:
        super().__init__()
        self.tasks = tasks
        self.save_root = Path(save_dir)
        self._cancelled = False
        self.downloader = FileDownloader()

    def cancel(self) -> None:
        self._cancelled = True

    def _should_cancel(self) -> bool:
        return self._cancelled

    @Slot()
    def run(self) -> None:
        completed = 0
        failed = 0
        skipped = 0
        total = len(self.tasks)

        try:
            for task in self.tasks:
                if self._should_cancel():
                    self.item_status.emit(task.index, "已取消")
                    continue

                self.item_status.emit(task.index, "下载中")
                try:
                    status = self.downloader.download(
                        task=task,
                        root_dir=self.save_root,
                        should_cancel=self._should_cancel,
                        progress_callback=self.item_progress.emit,
                        size_callback=self.item_size.emit,
                        log_callback=self.log.emit,
                    )
                    self.item_status.emit(task.index, status)
                    if status == "已完成":
                        completed += 1
                    elif status == "已跳过":
                        skipped += 1
                except DownloadCancelled as exc:
                    self.log.emit(str(exc))
                    self.item_status.emit(task.index, "已取消")
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    self.item_status.emit(task.index, "失败")
                    self.log.emit(f"下载失败({task.relative_path}): {exc}")

                self.summary.emit(total, completed, failed, skipped)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"下载失败: {exc}")
        finally:
            self.summary.emit(total, completed, failed, skipped)
            self.finished.emit()
