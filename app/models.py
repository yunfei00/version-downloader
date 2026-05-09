from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class DownloadTask:
    index: int
    relative_path: str
    file_url: str
    size: int | None = None
    status: str = "待下载"
    progress: int = 0

    def local_path(self, root_dir: Path) -> Path:
        return root_dir.joinpath(*Path(self.relative_path).parts)
