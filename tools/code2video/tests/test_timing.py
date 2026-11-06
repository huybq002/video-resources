from code2video.srt import group_scenes, parse_srt
from code2video.tts import DryRunTTS
from code2video.timeline import synthesize_cues


def test_parse_srt_and_scene_timing():
    cues = parse_srt("""1\n00:00:00,000 --> 00:00:02,000\nXin chào\n\n2\n00:00:02,000 --> 00:00:04,000\nHyperFrames\n""")
    assert [(cue.start_ms, cue.end_ms) for cue in cues] == [(0, 2000), (2000, 4000)]
    scenes = group_scenes(cues, target_sec=3, min_sec=0, max_sec=10)
    assert scenes[0].cue_range == (1, 2)


def test_synthesis_pushes_overlapping_cues():
    cues = parse_srt("""1\n00:00:00,000 --> 00:00:00,100\nMột câu dài\n\n2\n00:00:00,100 --> 00:00:00,200\nCâu hai\n""")
    timeline = synthesize_cues(cues, DryRunTTS(milliseconds_per_character=100), __import__('pathlib').Path('/tmp/code2video-test.wav'))
    assert timeline.cues[1].start_ms >= timeline.cues[0].end_ms
    assert timeline.cues[1].requested_start_ms == 100
