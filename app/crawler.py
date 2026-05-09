from __future__ import annotations

from collections import deque
from urllib.parse import parse_qs, unquote, urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class CrawlCancelled(Exception):
    pass


class DirectoryCrawler:
    def __init__(self, timeout: tuple[int, int] = (8, 20)) -> None:
        self.timeout = timeout

    def crawl(self, base_url: str, should_cancel, log_callback):
        normalized = base_url if base_url.endswith("/") else f"{base_url}/"
        root = urlparse(normalized)
        queue: deque[str] = deque([normalized])
        visited_dirs: set[str] = set()
        seen_files: set[str] = set()
        files: list[dict] = []

        while queue:
            if should_cancel():
                raise CrawlCancelled("扫描已取消")

            current_url = self._normalize_url(queue.popleft())
            if current_url in visited_dirs:
                continue
            visited_dirs.add(current_url)

            log_callback(f"扫描目录: {current_url}")
            response = requests.get(current_url, timeout=self.timeout)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            for link in soup.find_all("a", href=True):
                if should_cancel():
                    raise CrawlCancelled("扫描已取消")

                href = link["href"].strip()
                if not href or href == "#":
                    continue
                if self._should_skip_href(href):
                    continue

                absolute = self._normalize_url(urljoin(current_url, href))
                parsed = urlparse(absolute)

                if parsed.scheme not in ("http", "https"):
                    continue
                if parsed.netloc != root.netloc:
                    continue
                if not parsed.path.startswith(root.path):
                    continue

                rel_path = unquote(parsed.path[len(root.path):]).lstrip("/")
                if not rel_path:
                    continue

                if parsed.path.endswith("/"):
                    if absolute not in visited_dirs:
                        queue.append(absolute)
                    continue

                if absolute in seen_files:
                    continue

                seen_files.add(absolute)
                size = self._fetch_content_length(absolute)
                files.append({"relative_path": rel_path, "url": absolute, "size": size})
                log_callback(f"发现文件: {rel_path}")

        files.sort(key=lambda item: item["relative_path"])
        return files

    @staticmethod
    def _normalize_url(url: str) -> str:
        clean, _ = urldefrag(url)
        return clean

    @staticmethod
    def _should_skip_href(href: str) -> bool:
        lower = href.lower()
        if lower.startswith(("javascript:", "mailto:")):
            return True
        if href in ("../", ".."):
            return True
        if href.startswith("?"):
            query = parse_qs(href.lstrip("?"), keep_blank_values=True)
            if "c" in query and "o" in query:
                return True
        if any(token in href for token in ("?C=N", "?C=M", "?C=S", "?C=D")):
            return True
        return False

    def _fetch_content_length(self, url: str) -> int | None:
        try:
            response = requests.head(url, allow_redirects=True, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException:
            return None

        content_length = response.headers.get("Content-Length")
        if not content_length:
            return None

        try:
            size = int(content_length)
            return size if size >= 0 else None
        except ValueError:
            return None

        return None
