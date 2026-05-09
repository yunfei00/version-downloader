from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import QAbstractItemView, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget

from app.models import DownloadTask
from app.workers import DownloadManagerWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Version Downloader")
        self.resize(1040, 780)
        self.tasks: list[DownloadTask] = []
        self.worker_thread: QThread | None = None
        self.worker: DownloadManagerWorker | None = None
        self._download_start_at: float | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        cfg_box = QGroupBox("配置")
        cfg_layout = QGridLayout(cfg_box)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("例如: http://127.0.0.1:8000/releases/")
        self.save_edit = QLineEdit()
        browse_btn = QPushButton("选择目录")
        browse_btn.clicked.connect(self.select_save_dir)
        cfg_layout.addWidget(QLabel("根目录 URL"), 0, 0)
        cfg_layout.addWidget(self.url_edit, 0, 1, 1, 2)
        cfg_layout.addWidget(QLabel("保存目录"), 1, 0)
        cfg_layout.addWidget(self.save_edit, 1, 1)
        cfg_layout.addWidget(browse_btn, 1, 2)
        layout.addWidget(cfg_box)

        btn_layout = QHBoxLayout()
        self.scan_btn = QPushButton("扫描目录")
        self.download_btn = QPushButton("开始下载")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self.scan_directories)
        self.download_btn.clicked.connect(self.start_download)
        self.cancel_btn.clicked.connect(self.cancel_current)
        btn_layout.addWidget(self.scan_btn)
        btn_layout.addWidget(self.download_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.total_progress = QProgressBar(); self.total_progress.setRange(0, 100)
        layout.addWidget(self.total_progress)

        stats = QGridLayout()
        self.file_count_label = QLabel("文件总数: 0")
        self.total_size_label = QLabel("总大小: 0 B")
        self.downloaded_size_label = QLabel("已下载大小: 0 B")
        self.speed_label = QLabel("当前速度: 未知")
        self.elapsed_label = QLabel("已用时间: 00:00:00")
        self.eta_label = QLabel("预计剩余时间: 未知")
        self.phase_label = QLabel("当前阶段: 待命")
        labels = [self.file_count_label, self.total_size_label, self.downloaded_size_label, self.speed_label, self.elapsed_label, self.eta_label, self.phase_label]
        for i, lb in enumerate(labels):
            stats.addWidget(lb, i // 3, i % 3)
        layout.addLayout(stats)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["序号", "相对路径", "大小", "状态", "进度", "本地路径"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.log_edit = QTextEdit(); self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)

    def _run_worker(self, mode: str) -> None:
        url = self.url_edit.text().strip()
        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(self, "提示", "请输入有效 HTTP/HTTPS URL"); return
        save_dir = self.save_edit.text().strip()
        if mode != "scan_only" and not save_dir:
            QMessageBox.warning(self, "提示", "请选择保存目录"); return
        if save_dir:
            Path(save_dir).mkdir(parents=True, exist_ok=True)

        self.scan_btn.setEnabled(False); self.download_btn.setEnabled(False); self.cancel_btn.setEnabled(True)
        self.worker_thread = QThread(self)
        self.worker = DownloadManagerWorker(url, self.tasks, save_dir, mode)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.tasks_ready.connect(self.on_tasks_ready)
        self.worker.item_progress.connect(self.update_progress)
        self.worker.item_status.connect(self.update_status)
        self.worker.item_size.connect(self.update_size)
        self.worker.stats.connect(self.update_stats)
        self.worker.log.connect(self._log)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def scan_directories(self) -> None:
        self.tasks.clear(); self.table.setRowCount(0)
        self._run_worker("scan_only")

    def start_download(self) -> None:
        if not self.tasks:
            self.table.setRowCount(0)
            self._run_worker("scan_then_download")
        else:
            self._run_worker("download_only")
        self._download_start_at = time.time()

    def cancel_current(self) -> None:
        if self.worker:
            self.worker.cancel(); self._log("请求取消任务...")

    def on_tasks_ready(self, tasks: list[DownloadTask]) -> None:
        self.tasks = tasks
        self.table.setRowCount(0)
        for task in tasks:
            self._add_task_row(task)
        self._log(f"扫描完成，共 {len(tasks)} 个文件")

    def on_finished(self) -> None:
        self.scan_btn.setEnabled(True); self.download_btn.setEnabled(True); self.cancel_btn.setEnabled(False)
        if self._download_start_at:
            self._log(f"下载流程结束，总耗时: {self._format_duration(int(time.time()-self._download_start_at))}")
            self._download_start_at = None

    def _add_task_row(self, task: DownloadTask) -> None:
        row = self.table.rowCount(); self.table.insertRow(row)
        idx = QTableWidgetItem(str(task.index)); idx.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 0, idx)
        self.table.setItem(row, 1, QTableWidgetItem(task.relative_path))
        self.table.setItem(row, 2, QTableWidgetItem(self.format_size(task.size)))
        self.table.setItem(row, 3, QTableWidgetItem(task.status))
        self.table.setCellWidget(row, 4, QProgressBar())
        self.table.cellWidget(row, 4).setProperty("value", 0)
        self.table.setItem(row, 5, QTableWidgetItem(""))

    def update_progress(self, index: int, progress: int) -> None:
        row = index - 1
        widget = self.table.cellWidget(row, 4)
        if isinstance(widget, QProgressBar): widget.setValue(progress)
        self._focus_row(row)

    def update_status(self, index: int, status: str) -> None:
        row = index - 1
        if self.table.item(row, 3): self.table.item(row, 3).setText(status)
        if self.worker and self.table.item(row, 5):
            self.table.item(row, 5).setText(str(self.worker.tasks[row].local_path(self.worker.save_root)))
        self._focus_row(row)

    def update_size(self, index: int, size: int | None) -> None:
        row = index - 1
        if self.table.item(row, 2): self.table.item(row, 2).setText(self.format_size(size))

    def update_stats(self, payload: dict) -> None:
        self.file_count_label.setText(f"文件总数: {payload['file_count']}")
        known = self.format_size(payload['known_total_bytes'])
        unknown = payload['unknown_files']
        total_text = known if unknown == 0 else f"{known} + {unknown} 个未知文件"
        self.total_size_label.setText(f"总大小: {total_text}")
        self.downloaded_size_label.setText(f"已下载大小: {self.format_size(payload['downloaded_bytes'])}")
        speed = payload['speed_bps']
        self.speed_label.setText(f"当前速度: {self.format_size(int(speed))}/s" if speed > 0 else "当前速度: 未知")
        self.elapsed_label.setText(f"已用时间: {self._format_duration(payload['elapsed_seconds'])}")
        eta = payload['eta_seconds']
        self.eta_label.setText(f"预计剩余时间: {self._format_duration(eta)}" if eta is not None else "预计剩余时间: 未知")
        self.phase_label.setText(f"当前阶段: {payload['phase']}")
        total = payload['known_total_bytes']
        if total > 0:
            self.total_progress.setValue(min(100, int(payload['downloaded_bytes'] * 100 / total)))

    def _focus_row(self, row: int) -> None:
        if 0 <= row < self.table.rowCount():
            self.table.selectRow(row)
            item = self.table.item(row, 0)
            if item: self.table.scrollToItem(item, QAbstractItemView.PositionAtCenter)

    def select_save_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if directory: self.save_edit.setText(directory)

    @staticmethod
    def format_size(size_bytes: int | None) -> str:
        if size_bytes is None or size_bytes < 0: return "未知"
        units = ["B", "KB", "MB", "GB"]; value = float(size_bytes); i = 0
        while value >= 1024 and i < len(units) - 1: value /= 1024; i += 1
        return f"{int(value)} {units[i]}" if i == 0 else f"{value:.2f} {units[i]}"

    @staticmethod
    def _format_duration(seconds: int) -> str:
        h = seconds // 3600; m = (seconds % 3600) // 60; s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _on_error(self, message: str) -> None:
        self._log(message); QMessageBox.critical(self, "错误", message)

    def _log(self, message: str) -> None:
        self.log_edit.append(message)
