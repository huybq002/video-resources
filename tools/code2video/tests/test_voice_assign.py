from code2video.voice_assign import VIENEU_VOICES, assign_voices, guess_gender


def test_guess_gender():
    assert guess_gender("Bà Lan") == "female"
    assert guess_gender("Nguyễn Thị Hoa") == "female"
    assert guess_gender("Ông Tư") == "male"
    assert guess_gender("Trần Văn Hùng") == "male"
    assert guess_gender("An (nữ)") == "female"
    assert guess_gender("Minh [male]") == "male"
    assert guess_gender("An") is None
    assert guess_gender("Minh") is None


def test_distinct_voices_and_gender_match():
    pools = VIENEU_VOICES["v3turbo"]
    v = assign_voices(["Bà Lan", "Ông Tư", "Chị Hoa", "Anh Khoa"])
    assert v["Bà Lan"] in pools["female"] and v["Chị Hoa"] in pools["female"]
    assert v["Ông Tư"] in pools["male"] and v["Anh Khoa"] in pools["male"]
    assert len(set(v.values())) == 4


def test_neutral_names_balanced_and_distinct():
    pools = VIENEU_VOICES["v3turbo"]
    v = assign_voices(["An", "Minh"])
    assert v["An"] != v["Minh"]
    assert {v["An"] in pools["male"], v["Minh"] in pools["male"]} == {True, False}


def test_explicit_kept_and_not_reused():
    v = assign_voices(["An", "Bà Lan"], {"An": "Ngọc Huyền"})
    assert v["An"] == "Ngọc Huyền"
    assert v["Bà Lan"] != "Ngọc Huyền"


def test_more_speakers_than_voices_still_assigns():
    names = [f"Nhân vật {i}" for i in range(40)]
    v = assign_voices(names)
    assert len(v) == 40


def test_english_voices_by_name():
    from code2video.voice_assign import EDGE_GENDER

    assert guess_gender("Mrs. Smith") == "female"
    assert guess_gender("John") == "male"
    v = assign_voices(["Mary", "John", "Emma", "Tom", "Alex"], language="en")
    assert len(set(v.values())) == 5
    assert EDGE_GENDER[v["Mary"]] == "female" and EDGE_GENDER[v["Emma"]] == "female"
    assert EDGE_GENDER[v["John"]] == "male" and EDGE_GENDER[v["Tom"]] == "male"
    assert all(x.startswith("en-") for x in v.values())
