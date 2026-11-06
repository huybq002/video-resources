import pytest

from code2video.ai_script import demo_script, parse_script_payload, system_prompt, user_prompt


VALID = {
    "scenes": [
        {"title": "Mở đầu", "cues": [
            {"text": "Câu thoại một về chủ đề.", "doodle": "door", "label": "Cánh cửa"},
            {"text": "Câu thoại hai.", "doodle": "key", "label": "Chìa khóa"},
        ]},
    ]
}


def test_parse_script_payload_valid():
    parsed = parse_script_payload(VALID)
    assert parsed["scenes"][0]["cues"][0]["doodle"] == "door"
    assert parsed["scenes"][0]["cues"][1]["label"] == "Chìa khóa"


def test_parse_script_payload_rejects_unknown_doodle():
    bad = {"scenes": [{"title": "T", "cues": [{"text": "x", "doodle": "rocket", "label": ""}]}]}
    with pytest.raises(ValueError, match="rocket"):
        parse_script_payload(bad)


def test_parse_script_payload_rejects_empty_and_splits_too_many_cues():
    with pytest.raises(ValueError, match="scenes"):
        parse_script_payload({"scenes": []})
    many = {"scenes": [{"title": "T", "cues": [
        {"text": f"c{i}", "doodle": "question", "label": ""} for i in range(7)
    ]}]}
    parsed = parse_script_payload(many)["scenes"]  # quá 6 câu: tách scene, không báo lỗi
    assert [len(s["cues"]) for s in parsed] == [6, 1] and parsed[1]["title"] == "T (2)"
    with pytest.raises(ValueError, match="1-6"):
        parse_script_payload({"scenes": [{"title": "T", "cues": []}]})


def test_prompts_contain_schema_and_doodles():
    system = system_prompt("Kỹ năng thử.", "vi")
    assert "scenes" in system and "doodle" in system
    assert "door" in system
    user = user_prompt("thói quen buổi sáng", "vi", 3)
    assert "thói quen buổi sáng" in user and "3" in user


def test_demo_script_needs_no_key_and_parses():
    payload = demo_script("thói quen buổi sáng", "vi", 2)
    parsed = parse_script_payload(payload)
    assert parsed["scenes"]
    assert all(
        c["doodle"] in ("question", "arrow", "clock", "like", "wave")
        for s in parsed["scenes"] for c in s["cues"]
    )
