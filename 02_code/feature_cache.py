"""
feature_cache.py
多肽序列理化与 ESM-2 嵌入的多级缓存引擎 (内存 OrderedDict LRU + 本地磁盘 .npz 持久化)。
保证相同分子的 ESM-2 嵌入与理化特征毫秒级命中，避免重复计算耗竭 CPU/显存。
"""
from collections import OrderedDict
import hashlib
from pathlib import Path
import threading
from typing import Callable, Dict, Optional, Tuple
import numpy as np

from feature_extractor import clean_sequence, extract_handcrafted_features
from research_utils import ROOT


class SequenceFeatureCache:
    """
    多肽序列理化与 ESM-2 嵌入特征的多级缓存引擎。
    一级缓存: 内存 LRU (OrderedDict + threading.Lock)
    二级缓存: 磁盘压缩数组 (.npz, 目录采用 SHA-256 前两位分桶)
    """

    def __init__(self, cache_dir: Optional[Path] = None, max_memory_items: int = 512):
        self.cache_dir = Path(cache_dir or (ROOT / 'output' / 'cache' / 'features'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_memory_items = max_memory_items
        self._lock = threading.Lock()
        self._memory_cache: OrderedDict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _hash_key(self, seq: str) -> str:
        cleaned = clean_sequence(seq)
        return hashlib.sha256(cleaned.encode('utf-8')).hexdigest()

    def get_or_compute(
        self,
        seq: str,
        compute_fn: Optional[Callable[[str], Tuple[np.ndarray, np.ndarray, np.ndarray]]] = None,
        extractor = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        获取或计算序列的 (pooled_emb, residue_emb, handcrafted_phys) 特征元组。
        优先读取内存 LRU 缓存；若未命中读取磁盘 .npz 缓存；若仍未命中则调用 compute_fn 或 extractor 计算。
        """
        cleaned = clean_sequence(seq)
        key = self._hash_key(cleaned)

        # 1. 尝试从内存缓存中读取 (Cache Hit - Memory)
        with self._lock:
            if key in self._memory_cache:
                self._hits += 1
                self._memory_cache.move_to_end(key)
                return self._memory_cache[key]

        # 2. 尝试从磁盘持久化缓存读取 (.npz) (Cache Hit - Disk)
        disk_file = self.cache_dir / f"{key[:2]}/{key}.npz"
        if disk_file.is_file():
            try:
                with np.load(disk_file) as data:
                    pooled = np.array(data['pooled'])
                    residue = np.array(data['residue'])
                    phys = np.array(data['phys'])
                with self._lock:
                    self._hits += 1
                    self._put_memory(key, (pooled, residue, phys))
                return pooled, residue, phys
            except Exception:
                pass  # 若文件损坏或不可读则优雅降级为重新计算

        # 3. Cache Miss: 执行特征计算
        with self._lock:
            self._misses += 1

        if compute_fn is not None:
            pooled, residue, phys = compute_fn(cleaned)
        else:
            if extractor is None:
                raise ValueError("Either compute_fn or extractor must be provided.")
            pooled, residue = extractor.extract_sequence_embedding(cleaned)
            phys = extract_handcrafted_features(cleaned)

        # 4. 回写内存与磁盘
        with self._lock:
            self._put_memory(key, (pooled, residue, phys))

        try:
            disk_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = disk_file.with_suffix('.tmp.npz')
            np.savez_compressed(temp_file, pooled=pooled, residue=residue, phys=phys)
            temp_file.replace(disk_file)
        except Exception:
            pass  # 磁盘写入失败不阻断业务逻辑

        return pooled, residue, phys

    def _put_memory(self, key: str, value: Tuple[np.ndarray, np.ndarray, np.ndarray]):
        if key in self._memory_cache:
            self._memory_cache.move_to_end(key)
        else:
            self._memory_cache[key] = value
            while len(self._memory_cache) > self.max_memory_items:
                self._memory_cache.popitem(last=False)

    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                'hits': self._hits,
                'misses': self._misses,
                'memory_items': len(self._memory_cache),
                'total_queries': self._hits + self._misses
            }

    def clear(self, memory_only: bool = False):
        """清空缓存"""
        with self._lock:
            self._memory_cache.clear()
            self._hits = 0
            self._misses = 0
        if not memory_only and self.cache_dir.exists():
            for p in self.cache_dir.glob("*/*.npz"):
                try:
                    p.unlink()
                except Exception:
                    pass
