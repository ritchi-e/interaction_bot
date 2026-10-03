"""LRU PCM cache for repeated greetings / closings / handoff lines."""

from __future__ import annotations

import hashlib
import os
import threading
import time
from collections import OrderedDict
from pathlib import Path


class PcmCache:
    def __init__(
        self,
        *,
        max_items: int = 256,
        disk_dir: str | Path | None = None,
    ) -> None:
        self.max_items = max_items
        self.disk_dir = Path(disk_dir) if disk_dir else None
        if self.disk_dir:
            self.disk_dir.mkdir(parents=True, exist_ok=True)
        self._mem: OrderedDict[str, bytes] = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def key(voice: str, text: str) -> str:
        raw = f"{voice}\0{text}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def get(self, voice: str, text: str) -> bytes | None:
        k = self.key(voice, text)
        with self._lock:
            if k in self._mem:
                self._mem.move_to_end(k)
                return self._mem[k]
        if self.disk_dir:
            path = self.disk_dir / f"{k}.pcm"
            if path.exists():
                data = path.read_bytes()
                with self._lock:
                    self._mem[k] = data
                    self._mem.move_to_end(k)
                    while len(self._mem) > self.max_items:
                        self._mem.popitem(last=False)
                return data
        return None

    def put(self, voice: str, text: str, pcm: bytes) -> None:
        k = self.key(voice, text)
        with self._lock:
            self._mem[k] = pcm
            self._mem.move_to_end(k)
            while len(self._mem) > self.max_items:
                self._mem.popitem(last=False)
        if self.disk_dir and pcm:
            path = self.disk_dir / f"{k}.pcm"
            tmp = path.with_suffix(".part")
            tmp.write_bytes(pcm)
            tmp.replace(path)
