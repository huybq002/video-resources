"""Places for Bible-story films (hezb-motion): a hillside crowd, the rocky Jericho road, an inn at night and in the morning."""
from worlds import _sky, farm, tavern


def hillside(sky="day", **o):
    return {
        "sky": _sky(sky),
        "far": [{"type": "hills", "y": 600, "amp": 90, "color": "#b4d490"}, {"type": "hills", "y": 700, "amp": 60, "color": "#98c474"}],
        "mid": [{"type": "ground", "y": 800, "color": "#9fca78"}, {"type": "tree", "x": 140, "y": 830, "s": 1.2, "leaf": "#6f9e55"},
                {"type": "tree", "x": 1780, "y": 820, "s": 1.0, "leaf": "#7aa85e"}, {"type": "palm", "x": 1560, "y": 820, "s": 0.9}],
        "near": [{"type": "grass", "y": 900, "density": 0.5}],
        "ambient": [{"type": "clouds", "n": 4}, {"type": "birds", "every": 11, "y": 240},
                    {"type": "wheat", "y": 1010, "n": 40, "h": 70, "color": "#8faa4a", "head": "#c8d47a"}],
        "particles": [{"preset": "dust", "number": 30}],
        "look": {"grade": "warm", "light": [0.82, 0.16, 0.16]}, **o}


def jericho_road(sky="day", **o):
    return {
        "sky": _sky(sky),
        "far": [{"type": "dune", "y": 640, "amp": 90, "color": "#e3cf9f", "phase": 0.5}, {"type": "dune", "y": 720, "amp": 60, "color": "#d6bd88", "phase": 2.0}],
        "mid": [{"type": "ground", "y": 760, "color": "#d1b57e"}, {"type": "stones", "y": 800},
                {"type": "boulder", "x": 240, "y": 860, "s": 1.4}, {"type": "boulder", "x": 1640, "y": 840, "s": 1.1}, {"type": "boulder", "x": 1220, "y": 770, "s": 0.7}],
        "near": [{"type": "grass", "y": 980, "density": 0.15, "color": "#b9a65a", "dark": "#8a7a3a"}],
        "ambient": [{"type": "clouds", "n": 2, "color": "#f4efe2"}, {"type": "birds", "every": 16, "y": 220, "n": 3}],
        "particles": [{"preset": "dust", "number": 70}],
        "look": {"grade": "warm", "light": [0.85, 0.12, 0.14]}, **o}


def inn_night(**o):
    return {
        "sky": _sky("night"),
        "far": [{"type": "dune", "y": 680, "amp": 50, "color": "#2e3a5a", "phase": 1.0}],
        "mid": [{"type": "ground", "y": 800, "color": "#5a5a6e"},
                {"type": "house", "x": 640, "y": 830, "w": 640, "h": 340, "wall": "#8a8278", "roof": "#6a4a3a", "window": "#ffd77a", "door": "#ffcf6a"},
                {"type": "fence", "x0": 80, "x1": 560, "y": 860}, {"type": "palm", "x": 1700, "y": 840, "s": 1.1}],
        "near": [],
        "ambient": [{"type": "glow", "lights": [[960, 700, 300], [820, 640, 160]], "color": "#ffcf6a", "depth": "mid"}],
        "particles": [{"preset": "fireflies", "number": 24}],
        "look": {"grade": "night", "vignette": 0.5, "light": [0.5, 0.62, 0.18]}, **o}


def inn_room(**o):
    p = tavern()
    p["mid"] = [{"type": "window", "x": 1480, "y": 190, "w": 240, "h": 280, "glass": "#1d2550"}, {"type": "shelf", "x": 200, "y": 330, "w": 520, "n": 6},
                {"type": "planks", "y": 760, "color": "#7a5a3e"}]
    p["front"] = []
    p["ambient"] = [{"type": "glow", "lights": [[960, 480, 320]], "color": "#ffcf6a", "depth": "mid"}]
    p["look"] = {"grade": "warm", "vignette": 0.5, "light": [0.5, 0.45, 0.2]}
    p.update(o); return p


def inn_yard(**o):
    p = farm("morning")
    p["mid"] = [{"type": "ground", "y": 820, "color": "#d8c49a"},
                {"type": "house", "x": 1100, "y": 830, "w": 600, "h": 330, "wall": "#e2d2ae", "roof": "#a2563e"},
                {"type": "table", "x": 280, "y": 800, "w": 340}, {"type": "gate", "x": 1740, "y": 880, "w": 120}, {"type": "palm", "x": 160, "y": 840, "s": 1.0}]
    p["ambient"] = [{"type": "clouds", "n": 3}, {"type": "birds", "every": 9, "y": 240}, {"type": "smoke", "x": 1500, "y": 480, "depth": "mid"}]
    p.update(o); return p
