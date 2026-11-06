import numpy as np

from code2video.tts import CachedTTS


class FakeTTS:
    def __init__(self):
        self.calls = 0
        self.voice = "v1"
        self.sample_rate = 24000

    def synthesize(self, text):
        self.calls += 1
        return np.full(self.sample_rate // 10, 0.1, dtype=np.float32)


def test_cached_tts_reuses_audio_for_same_text_and_voice(tmp_path):
    inner = FakeTTS()
    cached = CachedTTS(inner, cache_dir=tmp_path, prefix="en:test")
    first = cached.synthesize("xin chào")
    second = cached.synthesize("xin chào")
    assert inner.calls == 1
    assert np.allclose(first, second, atol=0.001)
    assert len(list(tmp_path.glob("*.wav"))) == 1


def test_cached_tts_recomputes_when_voice_changes(tmp_path):
    inner = FakeTTS()
    cached = CachedTTS(inner, cache_dir=tmp_path, prefix="en:test")
    cached.synthesize("xin chào")
    cached.voice = "v2"
    cached.synthesize("xin chào")
    assert inner.calls == 2
    assert len(list(tmp_path.glob("*.wav"))) == 2


def test_cached_tts_shared_across_instances(tmp_path):
    inner = FakeTTS()
    one = CachedTTS(inner, cache_dir=tmp_path, prefix="en:test")
    two = CachedTTS(FakeTTS(), cache_dir=tmp_path, prefix="en:test")
    one.synthesize("xin chào")
    two.synthesize("xin chào")
    assert inner.calls == 1


def test_get_tts_wraps_edge_adapter_with_cache(monkeypatch, tmp_path):
    from code2video.studio import engines
    monkeypatch.setenv("TTS_CACHE_DIR", str(tmp_path))
    adapter = engines.get_tts(False, "v3turbo", "en")
    assert isinstance(adapter, CachedTTS)
    assert not isinstance(engines.get_tts(True, "v3turbo", "en"), CachedTTS)
