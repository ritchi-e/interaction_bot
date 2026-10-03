from cache import PcmCache


def test_memory_roundtrip(tmp_path):
    cache = PcmCache(max_items=2, disk_dir=tmp_path)
    cache.put("v1", "hello", b"\x01\x02")
    assert cache.get("v1", "hello") == b"\x01\x02"
    assert cache.get("v1", "other") is None


def test_disk_reload(tmp_path):
    cache = PcmCache(max_items=8, disk_dir=tmp_path)
    cache.put("v1", "namaste", b"pcm-bytes")
    other = PcmCache(max_items=8, disk_dir=tmp_path)
    assert other.get("v1", "namaste") == b"pcm-bytes"


def test_lru_eviction(tmp_path):
    cache = PcmCache(max_items=2, disk_dir=None)
    cache.put("v", "a", b"a")
    cache.put("v", "b", b"b")
    cache.put("v", "c", b"c")
    assert cache.get("v", "a") is None
    assert cache.get("v", "b") == b"b"
    assert cache.get("v", "c") == b"c"
