"""Ready-made places for hezb-motion films (B2 colourful hand-drawn world). Each returns a place spec for film.json:
sky, far/mid/near layers (paper.js shapes + p5 textures), ambient life, particles and a look (grade, light).
Start from one and change it for the story: the place must be the one the words name, with its signature objects.
"""


def _sky(kind):
    return {
        "morning": {"top": "#9fd3ec", "bottom": "#f8ead0", "sun": [1520, 210, 70]},
        "day": {"top": "#a7d8f0", "bottom": "#eef3e6", "sun": [1600, 160, 60]},
        "overcast": {"top": "#a9b3bd", "bottom": "#d9d6cc"},
        "rain": {"top": "#7f8a96", "bottom": "#b8bcbc"},
        "dusk": {"top": "#f0a560", "bottom": "#f9dfb0", "sun": [460, 760, 120], "sunColor": "#ffe2a0"},
        "sunset": {"top": "#f28a5b", "bottom": "#fbd38e", "sun": [380, 720, 130], "sunColor": "#ffe7a8"},
        "night": {"top": "#16224a", "bottom": "#3a3f6b", "stars": True, "moon": [1500, 170, 46]},
    }[kind]


def farm(sky="morning", **o):
    return {
        "sky": _sky(sky),
        "far": [{"type": "hills", "y": 640, "amp": 100, "color": "#a8cc84"}, {"type": "hills", "y": 720, "amp": 60, "color": "#8fbf6a"}],
        "mid": [{"type": "ground", "y": 820, "color": "#dcc79c"}, {"type": "house", "x": 1220, "y": 830, "w": 420, "h": 260, "chimney": True},
                {"type": "tree", "x": 300, "y": 830, "s": 1.15, "leaf": "#6f9e55"}, {"type": "tree", "x": 820, "y": 820, "s": 0.8, "leaf": "#7aa85e"},
                {"type": "fence", "x0": 40, "x1": 1100, "y": 860}, {"type": "well", "x": 1700, "y": 860}],
        "near": [{"type": "grass", "y": 950, "density": 0.35}],
        "ambient": [{"type": "clouds", "n": 4}, {"type": "birds", "every": 9, "y": 250}, {"type": "smoke", "x": 1530, "y": 500, "depth": "mid"},
                    {"type": "wheat", "y": 1000, "n": 50, "h": 80, "color": "#8faa4a", "head": "#c8d47a"}],
        "particles": [{"preset": "dust", "number": 40}],
        "look": {"grade": "warm", "light": [0.79, 0.19, 0.18]}, **o}


def tavern(**o):
    return {
        "sky": {"top": "#3a2a24", "bottom": "#5a4030"},
        "far": [{"type": "wall", "y": 760, "color": "#6e4c38"}, {"type": "bricks", "y0": 0, "y1": 760}],
        "mid": [{"type": "window", "x": 160, "y": 170, "w": 240, "h": 280, "glass": "#1d2550"}, {"type": "window", "x": 1500, "y": 170, "w": 240, "h": 280, "glass": "#1d2550"},
                {"type": "shelf", "x": 620, "y": 330, "w": 680, "n": 8}, {"type": "door", "x": 90, "y": 760, "w": 190, "h": 360, "color": "#5a3a26"},
                {"type": "planks", "y": 760, "color": "#7a5a3e"}],
        "front": [{"type": "table", "x": 380, "y": 780, "w": 1160, "h": 130}],
        "near": [],
        "ambient": [{"type": "glow", "lights": [[560, 260, 230], [1360, 260, 230]], "depth": "mid"}, {"type": "fire", "x": 1760, "y": 760, "s": 0.9, "depth": "mid"}],
        "particles": [{"preset": "dust", "number": 30}],
        "look": {"grade": "warm", "vignette": 0.5, "light": [0.3, 0.25, 0.12]}, **o}


def street(sky="overcast", **o):
    return {
        "sky": _sky(sky),
        "far": [{"type": "house", "x": -60, "y": 700, "w": 420, "h": 380, "wall": "#c9bfae", "roof": "#8a6a5a"}, {"type": "house", "x": 1440, "y": 700, "w": 520, "h": 360, "wall": "#bdb3a0", "roof": "#7a5a4a"}],
        "mid": [{"type": "ground", "y": 800, "color": "#b9b2a2"}, {"type": "stones", "y": 820}, {"type": "house", "x": 640, "y": 820, "w": 640, "h": 420, "wall": "#d6cbb5", "roof": "#6e5444"},
                {"type": "door", "x": 1010, "y": 820, "w": 170, "h": 300, "color": "#4f3624"}, {"type": "stall", "x": 260, "y": 840, "w": 280, "awning": "#8a7a6a"}],
        "near": [],
        "ambient": [{"type": "passers", "y": 800, "every": 3.5, "depth": "mid"}, {"type": "clouds", "n": 3, "color": "#e3e1dc"}],
        "particles": [{"preset": "leaves", "number": 14}],
        "look": {"grade": "grey"}, **o}


def pig_farm(sky="rain", **o):
    return {
        "sky": _sky(sky),
        "far": [{"type": "hills", "y": 650, "amp": 70, "color": "#8a9a7a"}, {"type": "shack", "x": 1480, "y": 760, "w": 300, "h": 220}],
        "mid": [{"type": "ground", "y": 780, "color": "#8a6e50"}, {"type": "mud", "x0": 0, "x1": 1920, "y": 800}, {"type": "pen", "x0": 820, "x1": 1820, "y": 850},
                {"type": "trough", "x": 1100, "y": 900, "w": 260}],
        "near": [],
        "ambient": [{"type": "pigs", "pigs": [[1000, 930, 1, 0.9], [1450, 960, -1, 1.0], [1650, 900, 1, 0.8]], "depth": "mid"},
                    {"type": "ripples", "puddles": [[300, 980, 110], [700, 1020, 80], [1500, 1040, 120]], "depth": "mid"}],
        "particles": [{"preset": "rain", "number": 240, "near": True}, {"preset": "flies", "area": [900, 760, 900, 260]}],
        "look": {"grade": "cool", "vignette": 0.45}, **o}


def road(sky="dusk", **o):
    return {
        "sky": _sky(sky),
        "far": [{"type": "hills", "y": 620, "amp": 120, "color": "#c9b77a"}, {"type": "house", "x": 1480, "y": 560, "w": 120, "h": 80}],
        "mid": [{"type": "ground", "y": 700, "color": "#d7c08a"}, {"type": "road", "vx": 1500, "y": 640, "color": "#c8ad78"}, {"type": "sign", "x": 1180, "y": 880},
                {"type": "tree", "x": 200, "y": 760, "s": 0.9, "leaf": "#8a9a4e"}],
        "near": [{"type": "grass", "y": 960, "density": 0.3, "color": "#b9a65a", "dark": "#8a7a3a"}],
        "ambient": [{"type": "birds", "every": 10, "y": 300}, {"type": "wheat", "y": 1010, "n": 60, "h": 70, "color": "#b0903a"}],
        "particles": [{"preset": "dust", "number": 60}],
        "look": {"grade": "dusk", "light": [0.24, 0.7, 0.22]}, **o}


def gate(sky="dusk", **o):
    p = farm(sky)
    p["mid"] = p["mid"] + [{"type": "gate", "x": 1020, "y": 880, "w": 280}]
    p["far"] = [{"type": "hills", "y": 660, "amp": 90, "color": "#c8b07a"}, {"type": "hills", "y": 740, "amp": 50, "color": "#b49a64"}]
    p["look"] = {"grade": "dusk", "light": [0.24, 0.7, 0.2]}
    p.update(o); return p


def wheat(sky="sunset", **o):
    return {
        "sky": _sky(sky),
        "far": [{"type": "hills", "y": 680, "amp": 70, "color": "#c9a24e"}, {"type": "house", "x": 1450, "y": 700, "w": 300, "h": 190, "window": "#ffd77a"}],
        "mid": [{"type": "field", "y": 700, "color": "#e2b84e", "dark": "#b98a2e"}],
        "near": [],
        "ambient": [{"type": "wheat", "y": 1000, "n": 170, "h": 150, "gusts": o.pop("gusts", [])}, {"type": "birds", "every": 12, "y": 260}],
        "particles": [{"preset": "dust", "number": 50}],
        "look": {"grade": "dusk", "light": [0.2, 0.66, 0.25]}, **o}


def gate_night(**o):
    p = gate("night")
    p["far"] = [{"type": "hills", "y": 660, "amp": 90, "color": "#2e3a5a"}, {"type": "hills", "y": 740, "amp": 50, "color": "#38456a"}]
    p["mid"] = [{"type": "ground", "y": 820, "color": "#4a4a5e"}, {"type": "house", "x": 1220, "y": 830, "w": 420, "h": 260, "wall": "#8a8278", "roof": "#5a3a3a", "window": "#ffd77a", "door": "#ffcf6a"},
                {"type": "gate", "x": 300, "y": 880, "w": 320}, {"type": "fence", "x0": 640, "x1": 1180, "y": 870}]
    p["ambient"] = [{"type": "glow", "lights": [[1360, 680, 260], [1580, 690, 160]], "color": "#ffcf6a", "depth": "mid"}]
    p["particles"] = [{"preset": "fireflies", "number": 40}]
    p["look"] = {"grade": "night", "vignette": 0.55, "light": [0.75, 0.62, 0.16]}
    p.update(o); return p
