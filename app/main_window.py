from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models import DownloadTask
from app.workers import DownloadWorker, ScanWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Version Downloader")
        self.resize(1000, 700)

        self.tasks: list[DownloadTask] = []
        self.scan_thread: QThread | None = None
        self.scan_worker: ScanWorker | None = None
        self.download_thread: QThread | None = None
        self.download_worker: DownloadWorker | None = None

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
        self.cancel_scan_btn = QPushButton("取消扫描")
        self.download_btn = QPushButton("开始下载")
        self.cancel_download_btn = QPushButton("取消下载")
        self.cancel_scan_btn.setEnabled(False)
        self.cancel_download_btn.setEnabled(False)

        self.scan_btn.clicked.connect(self.scan_directories)
        self.cancel_scan_btn.clicked.connect(self.cancel_scan)
        self.download_btn.clicked.connect(self.start_download)
        self.cancel_download_btn.clicked.connect(self.cancel_download)

        btn_layout.addWidget(self.scan_btn)
        btn_layout.addWidget(self.cancel_scan_btn)
        btn_layout.addWidget(self.download_btn)
        btn_layout.addWidget(self.cancel_download_btn)
        layout.addLayout(btn_layout)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["序号", "相对路径", "大小", "状态", "进度"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(1, 460)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 120)
        layout.addWidget(self.table)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)

    def select_save_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if directory:
            self.save_edit.setText(directory)

    def scan_directories(self) -> None:
        url = self.url_edit.text().strip()
        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(self, "提示", "请输入有效 HTTP/HTTPS URL")
            return

        self.tasks.clear()
        self.table.setRowCount(0)
        self._log("开始扫描目录...")
        self.scan_btn.setEnabled(False)
        self.cancel_scan_btn.setEnabled(True)

        self.scan_thread = QThread(self)
        self.scan_worker = ScanWorker(url)
        self.scan_worker.moveToThread(self.scan_thread)

        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.log.connect(self._log)
        self.scan_worker.error.connect(self._on_error)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)

        self.scan_thread.start()

    def cancel_scan(self) -> None:
        if self.scan_worker:
            self.scan_worker.cancel()
            self._log("请求取消扫描...")

    def on_scan_finished(self, tasks: list[DownloadTask]) -> None:
        self.tasks = tasks
        self.scan_btn.setEnabled(True)
        self.cancel_scan_btn.setEnabled(False)

        for task in tasks:
            self._add_task_row(task)

        self._log(f"扫描完成，共 {len(tasks)} 个文件")

    def _add_task_row(self, task: DownloadTask) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(task.index)))
        self.table.setItem(row, 1, QTableWidgetItem(task.relative_path))
        size_text = str(task.size) if task.size is not None else "-"
        self.table.setItem(row, 2, QTableWidgetItem(size_text))
        self.table.setItem(row, 3, QTableWidgetItem(task.status))

        bar = QProgressBar()
        bar.setValue(task.progress)
        self.table.setCellWidget(row, 4, bar)

    def start_download(self) -> None:
        if not self.tasks:
            QMessageBox.warning(self, "提示", "请先扫描目录")
            return

        save_dir = self.save_edit.text().strip()
        if not save_dir:
            QMessageBox.warning(self, "提示", "请选择保存目录")
            return

        Path(save_dir).mkdir(parents=True, exist_ok=True)
        self.download_btn.setEnabled(False)
        self.cancel_download_btn.setEnabled(True)
        self._log("开始下载...")

        self.download_thread = QThread(self)
        self.download_worker = DownloadWorker(self.tasks, save_dir)
        self.download_worker.moveToThread(self.download_thread)

        self.download_thread.started.connect(self.download_worker.run)
        self.download_worker.item_progress.connect(self.update_progress)
        self.download_worker.item_status.connect(self.update_status)
        self.download_worker.log.connect(self._log)
        self.download_worker.error.connect(self._on_error)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.finished.connect(self.download_thread.quit)
        self.download_thread.finished.connect(self.download_thread.deleteLater)

        self.download_thread.start()

    def cancel_download(self) -> None:
        if self.download_worker:
            self.download_worker.cancel()
            self._log("请求取消下载...")

    def on_download_finished(self) -> None:
        self.download_btn.setEnabled(True)
        self.cancel_download_btn.setEnabled(False)
        self._log("下载流程结束")

    def update_progress(self, index: int, progress: int) -> None:
        row = index - 1
        widget = self.table.cellWidget(row, 4)
        if isinstance(widget, QProgressBar):
            widget.setValue(progress)

    def update_status(self, index: int, status: str) -> None:
        row = index - 1
        item = self.table.item(row, 3)
        if item:
            item.setText(status)

    def _on_error(self, message: str) -> None:
        self._log(message)
        QMessageBox.critical(self, "错误", message)

    def _log(self, message: str) -> None:
        self.log_edit.append(message)
