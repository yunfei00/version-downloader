from __future__ import annotations

import re
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class CrawlCancelled(Exception):
    pass


class DirectoryCrawler:
    def __init__(self, timeout: tuple[int, int] = (8, 20)) -> None:
        self.timeout = timeout

    def crawl(self, base_url: str, should_cancel, log_callback):
        normalized = base_url if base_url.endswith("/") else f"{base_url}/"
        visited: set[str] = set()
        files: list[dict] = []

        def walk(current_url: str, rel_prefix: str = "") -> None:
            if should_cancel():
                raise CrawlCancelled("扫描已取消")
            if current_url in visited:
                return
            visited.add(current_url)

            log_callback(f"扫描: {current_url}")
            response = requests.get(current_url, timeout=self.timeout)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return

            soup = BeautifulSoup(response.text, "html.parser")
            for link in soup.find_all("a", href=True):
                if should_cancel():
                    raise CrawlCancelled("扫描已取消")

                href = link["href"].strip()
                if href in ("", "#"):
                    continue
                if href.startswith(("?", "javascript:", "mailto:")):
                    continue

                absolute = urljoin(current_url, href)
                parsed_base = urlparse(normalized)
                parsed_abs = urlparse(absolute)
                if parsed_abs.scheme not in ("http", "https"):
                    continue
                if parsed_abs.netloc != parsed_base.netloc:
                    continue
                if not parsed_abs.path.startswith(parsed_base.path):
                    continue

                name = unquote(parsed_abs.path[len(parsed_base.path):]).lstrip("/")
                if not name:
                    continue
                if name.endswith("/"):
                    walk(absolute if absolute.endswith("/") else absolute + "/", name)
                    continue
                if name in ("..", "/") or name.startswith("../"):
                    continue

                size = self._extract_size(link)
                files.append({"relative_path": name, "url": absolute, "size": size})

        walk(normalized)
        dedup = {}
        for item in files:
            dedup[item["relative_path"]] = item
        return list(dedup.values())

    @staticmethod
    def _extract_size(link_tag) -> int | None:
        row_text = " ".join(link_tag.parent.get_text(" ", strip=True).split()) if link_tag.parent else ""
        match = re.search(r"\b(\d{1,12})\b", row_text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None
