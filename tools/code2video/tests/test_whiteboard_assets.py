import json

from PIL import Image

from code2video.whiteboard_assets import DOODLES, build_scene_folder, draw_scene, locale_fonts


def test_locale_fonts_cover_languages():
    assert locale_fonts("vi")[0].endswith("segoeuib.ttf")
    assert "YuGoth" in locale_fonts("ja")[0]


def test_build_scene_folder_writes_png_annotation_srt(tmp_path):
    items = [
        ("door", "Cửa khóa", "Căn phòng bị khóa trái từ bên trong."),
        ("key", "Chìa khóa", "Nhưng chìa khóa vẫn nằm ở ổ bên trong."),
    ]
    result = build_scene_folder(tmp_path / "scene-01", "scene-01", "Mở đầu", items, "vi")

    image = Image.open(tmp_path / "scene-01" / "scene-01.png")
    assert image.size == (1920, 1080)

    annotation = json.loads((tmp_path / "scene-01" / "scene-01.annotation.json").read_text(encoding="utf-8"))
    assert annotation["sceneId"] == "scene-01"
    assert len(annotation["elements"]) == 2
    first = annotation["elements"][0]
    assert first["reveal"]["startMs"] == 0
    assert first["reveal"]["durationMs"] >= 700
    assert annotation["sceneDurationMs"] == result["durationMs"] == sum(
        e["reveal"]["durationMs"] + 120 for e in annotation["elements"]
    )

    srt = (tmp_path / "scene-01" / "script.srt").read_text(encoding="utf-8")
    assert srt.count("-->") == 2
    assert "Căn phòng bị khóa" in srt


def test_draw_scene_contains_ink_and_paper(tmp_path):
    img = draw_scene("Tiêu đề", [("question", "Nhãn", "Sub")], *locale_fonts("vi"))
    assert img.size == (1920, 1080)
    pixels = list(img.getdata())
    paper = (247, 244, 234)
    ink = sum(1 for p in pixels if p != paper)
    assert ink > 2000


def test_doodles_registry_has_expected_keys():
    assert {"mansion", "door", "window", "question", "arrow", "clock"}.issubset(DOODLES)


def test_label_fits_inside_reveal_region():
    """Nhãn nằm trọn trong vùng lộ (ô trừ lề 14px); trước đây nửa dưới chữ bị cắt khi quay video."""
    from code2video.whiteboard_assets import FONT_REG, LABEL_OFFSET, font

    label_font = font(FONT_REG, 34)
    bottom_of_text = label_font.getbbox("Ágjpqy")[3]
    assert bottom_of_text <= LABEL_OFFSET - 14
