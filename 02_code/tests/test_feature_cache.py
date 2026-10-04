import pytest
import numpy as np
from pathlib import Path
import threading
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '02_code'))
from feature_cache import SequenceFeatureCache


def test_cache_miss_and_hit(tmp_path):
    cache = SequenceFeatureCache(cache_dir=tmp_path / 'cache', max_memory_items=5)
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"

    call_count = 0
    def mock_compute(s):
        nonlocal call_count
        call_count += 1
        return np.ones(320, dtype=np.float32), np.ones((len(s), 320), dtype=np.float32), np.zeros(44, dtype=np.float32)

    # 第一次查询：Cache Miss
    p1, r1, h1 = cache.get_or_compute(seq, compute_fn=mock_compute)
    assert call_count == 1
    assert p1.shape == (320,)
    assert h1.shape == (44,)

    # 第二次查询：Cache Hit (内存命中)
    p2, r2, h2 = cache.get_or_compute(seq, compute_fn=mock_compute)
    assert call_count == 1  # 不应触发重新计算
    np.testing.assert_array_equal(p1, p2)

    # 统计数据校验
    stats = cache.get_stats()
    assert stats['hits'] == 1
    assert stats['misses'] == 1
    assert stats['memory_items'] == 1
    assert stats['total_queries'] == 2


def test_cache_disk_persistence(tmp_path):
    cache_dir = tmp_path / 'disk_cache'
    cache1 = SequenceFeatureCache(cache_dir=cache_dir, max_memory_items=1)
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"

    call_count = 0
    def mock_compute(s):
        nonlocal call_count
        call_count += 1
        return np.ones(320, dtype=np.float32) * 2.0, np.ones((len(s), 320), dtype=np.float32), np.zeros(44, dtype=np.float32)

    cache1.get_or_compute(seq, compute_fn=mock_compute)
    assert call_count == 1

    # 创建新实例（内存为空），应从磁盘读取
    cache2 = SequenceFeatureCache(cache_dir=cache_dir, max_memory_items=1)
    p2, _, _ = cache2.get_or_compute(seq, compute_fn=mock_compute)
    assert call_count == 1  # 依然不需要计算，命中磁盘缓存
    assert p2[0] == 2.0

    stats = cache2.get_stats()
    assert stats['hits'] == 1
    assert stats['misses'] == 0


def test_cache_lru_eviction(tmp_path):
    cache = SequenceFeatureCache(cache_dir=tmp_path / 'lru_cache', max_memory_items=2)
    seqs = [
        "GIGAVLKVLTTGLPALISWIKRKRQQ",
        "KWKLFKKIEKVGQNIRDGIIKAGPAVAVVGQATQIAK",
        "GLFDIVKKVVGALGSL"
    ]
    def mock_compute(s):
        return np.zeros(320, dtype=np.float32), np.zeros((len(s), 320), dtype=np.float32), np.zeros(44, dtype=np.float32)

    for s in seqs:
        cache.get_or_compute(s, compute_fn=mock_compute)

    stats = cache.get_stats()
    assert stats['memory_items'] == 2


def test_corrupted_disk_cache_fallback(tmp_path):
    cache_dir = tmp_path / 'corrupt_cache'
    cache = SequenceFeatureCache(cache_dir=cache_dir, max_memory_items=1)
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"

    call_count = 0
    def mock_compute(s):
        nonlocal call_count
        call_count += 1
        return np.ones(320, dtype=np.float32), np.ones((len(s), 320), dtype=np.float32), np.zeros(44, dtype=np.float32)

    cache.get_or_compute(seq, compute_fn=mock_compute)
    assert call_count == 1

    # 找到磁盘文件并故意破坏内容
    disk_files = list(cache_dir.glob("*/*.npz"))
    assert len(disk_files) == 1
    disk_files[0].write_bytes(b"corrupted binary data")

    # 创建新实例读取破坏的文件，应优雅降级为重新计算
    cache2 = SequenceFeatureCache(cache_dir=cache_dir, max_memory_items=1)
    cache2.get_or_compute(seq, compute_fn=mock_compute)
    assert call_count == 2


def test_invalid_sequence_rejection(tmp_path):
    cache = SequenceFeatureCache(cache_dir=tmp_path / 'cache')
    with pytest.raises(ValueError):
        cache.get_or_compute("123XYZINVALID")


def test_multithreaded_cache_access(tmp_path):
    cache = SequenceFeatureCache(cache_dir=tmp_path / 'mt_cache', max_memory_items=10)
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"

    call_count = 0
    def mock_compute(s):
        nonlocal call_count
        call_count += 1
        return np.ones(320, dtype=np.float32), np.ones((len(s), 320), dtype=np.float32), np.zeros(44, dtype=np.float32)

    threads = []
    for _ in range(10):
        t = threading.Thread(target=lambda: cache.get_or_compute(seq, compute_fn=mock_compute))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    stats = cache.get_stats()
    assert stats['total_queries'] == 10
    # 至少第一次 miss，后续并发可能命中
    assert stats['hits'] + stats['misses'] == 10


def test_cache_with_mock_extractor(tmp_path):
    cache = SequenceFeatureCache(cache_dir=tmp_path / 'extractor_cache')
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"

    class MockExtractor:
        def __init__(self):
            self.call_count = 0
        def extract_sequence_embedding(self, s):
            self.call_count += 1
            return np.ones(320, dtype=np.float32), np.ones((len(s), 320), dtype=np.float32)

    mock_ext = MockExtractor()
    pooled, residue, phys = cache.get_or_compute(seq, extractor=mock_ext)
    assert mock_ext.call_count == 1
    assert pooled.shape == (320,)
    assert residue.shape == (len(seq), 320)
    assert phys.shape == (44,)

    # 第二次读取应直接命中缓存
    pooled2, residue2, phys2 = cache.get_or_compute(seq, extractor=mock_ext)
    assert mock_ext.call_count == 1
    np.testing.assert_array_equal(pooled, pooled2)
    np.testing.assert_array_equal(phys, phys2)


def test_cache_missing_computation_args(tmp_path):
    cache = SequenceFeatureCache(cache_dir=tmp_path / 'cache')
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"
    with pytest.raises(ValueError, match="Either compute_fn or extractor must be provided"):
        cache.get_or_compute(seq)

