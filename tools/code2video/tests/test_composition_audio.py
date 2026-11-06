import numpy as np

from code2video.tts import DryRunTTS
from code2video.voice_assign import assign_voices
from code2video.voiceover import build_from_script, sync_composition_audio

SCRIPT = (
    "[Lan][00:00:00,000 --> 00:00:02,000][nữ]: Xin chào\n\n"
    "[Minh][00:00:02,000 --> 00:00:04,000][nam]: Chào Lan\n"
)
HTML = "<div id='root'><audio id='voice' src='assets/audio/voiceover.wav' data-start='0'></audio></div>"


def test_voiceover_is_copied_to_the_path_the_composition_expects(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    (project / "index.html").write_text(HTML, encoding="utf-8")
    script = project / "script.srt"
    script.write_text(SCRIPT, encoding="utf-8")
    result = build_from_script(project, script, DryRunTTS())
    assert (project / "voiceover.wav").is_file()
    assert (project / "assets" / "audio" / "voiceover.wav").is_file()
    assert result["audioCopy"].endswith("voiceover.wav")


def test_sync_ignores_remote_absolute_and_escaping_paths(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    wav = project / "voiceover.wav"
    wav.write_bytes(b"x")
    for src in ("http://x/a.wav", "/abs/a.wav", "../outside.wav", "data:audio/wav;base64,AAAA"):
        (project / "index.html").write_text(f"<audio src='{src}'></audio>", encoding="utf-8")
        assert sync_composition_audio(project, wav) is None
    assert not (tmp_path / "outside.wav").exists()


def test_assign_voices_uses_explicit_genders_over_name_guess():
    class Tts:  # chỉ cần có thuộc tính voice/mode
        voice = None
        mode = "v3turbo"

    plain = assign_voices(["An", "Bình"], {}, mode="v3turbo", language="vi", genders={"An": "female", "Bình": "male"})
    from code2video.voice_assign import _pools

    pools = _pools("v3turbo", "vi")
    assert plain["An"] in pools["female"] and plain["Bình"] in pools["male"]
