import pytest

from code2video.script_parse import parse_script

MULTI = """[An][00:00:00,000 --> 00:00:03,500]: Chào Minh.

[Minh][00:00:03,500 --> 00:00:07,000]: Chào An.
"""


def test_scene_comment_glued_above_a_speaker_block_does_not_swallow_the_line():
    text = "# SCENE 1 | quán cà phê\n" + MULTI + "\n# SCENE 2 | công viên\n[An][00:00:07,000 --> 00:00:10,000]: Mình đi dạo nhé.\n"
    lines, speakers = parse_script(text)
    assert [(l.speaker, l.text) for l in lines] == [("An", "Chào Minh."), ("Minh", "Chào An."), ("An", "Mình đi dạo nhé.")]
    assert speakers == ["An", "Minh"]


def test_scene_comment_as_its_own_block_is_ignored():
    lines, _ = parse_script("# SCENE 1\n\n" + MULTI + "\n# SCENE 2\n\n[An][00:00:07,000 --> 00:00:09,000]: Hết.\n")
    assert [l.text for l in lines] == ["Chào Minh.", "Chào An.", "Hết."]


def test_plain_srt_with_scene_comments_still_works():
    srt = "# SCENE 1 | a\n1\n00:00:00,000 --> 00:00:03,000\nMột.\n\n# SCENE 2 | b\n2\n00:00:03,000 --> 00:00:06,000\nHai.\n"
    lines, speakers = parse_script(srt)
    assert [(l.index, l.speaker, l.text) for l in lines] == [(1, "", "Một."), (2, "", "Hai.")] and speakers == []


def test_mixing_plain_srt_blocks_into_a_speaker_script_is_an_error_not_a_silent_drop():
    mixed = "[An][00:00:00,000 --> 00:00:03,000]: Có nhân vật.\n\n3\n00:00:03,000 --> 00:00:06,000\nKhông có nhân vật.\n"
    with pytest.raises(ValueError, match="sai định dạng"):
        parse_script(mixed)


def test_wrapped_speaker_lines_are_joined_and_cues_sorted_by_time():
    text = "[B][00:00:05,000 --> 00:00:08,000]: Sau.\n\n[A][00:00:00,000 --> 00:00:05,000]: Dòng một\ndòng hai.\n"
    lines, _ = parse_script(text)
    assert [(l.index, l.speaker, l.text) for l in lines] == [(1, "A", "Dòng một dòng hai."), (2, "B", "Sau.")]
