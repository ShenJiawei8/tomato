#!/usr/bin/env python3
# coding=utf-8
"""
Printing helpers for the Tomato timer.

This module currently exposes a single helper:

- ``PrintCache``: a lightweight buffered printer that accumulates
  output in memory and flushes to stdout or a file in one shot.

把打印逻辑从核心业务中抽出来，方便：
- 复用统一的输出行为（带缓冲）；
- 在测试或其他前端中替换为自定义实现。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PrintCache:
    """
    Buffered printer.

    使用方式示例::

        printer = PrintCache()
        printer.add("line 1")
        printer.add("line 2", "extra")
        printer.print()   # 一次性输出到 stdout

    - 如果传入 ``local_file``，则会把所有内容追加写入到该文件；
    - 每次调用 ``print`` 后，内部缓存都会被清空。
    """

    local_file: Optional[str] = None
    cache: str = ""

    def add(self, *segs: str, endl: bool = True) -> None:
        """
        Append one logical line to the cache.

        :param segs: 组成该行的若干字符串，会用空格拼接
        :param endl: 是否在末尾自动追加换行符
        """
        output = " ".join(segs)
        if endl:
            output += "\n"
        self.cache += output

    def get_cache(self) -> str:
        """Return the current in‑memory buffer."""
        return self.cache

    def clear_cache(self) -> None:
        """Clear the internal buffer without printing."""
        self.cache = ""

    def print(self) -> None:
        """
        Flush the current buffer to stdout or a file.

        - 当 ``local_file`` 为 ``None`` 时，直接 ``print`` 到控制台；
        - 否则以追加模式写入到文件末尾。
        """
        if self.local_file is None:
            # flush=True 以避免在长时间运行的 CLI 中缓冲滞留
            print(self.cache, flush=True)
        else:
            with open(self.local_file, "a", encoding="utf-8") as fout:
                fout.write(self.cache + "\n")
        self.clear_cache()


