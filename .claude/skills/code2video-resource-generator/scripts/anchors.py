"""Where the furniture of a 3D setting lands on screen, so characters and props can USE it.

The backgrounds are rendered in 3D, the characters are 2D drawings on top. Before this module a character told to
lie in bed lay down wherever it stood (on the floor in front of the bed), "sits at her desk" stood in front of the desk,
and a phone "left by the oven" floated in the air at the size of a torso. Now generate.py projects every furniture
piece through the same camera three.js uses and writes assets/anchors_<setting>.json; build_project.py places a
character or a prop on those points:

    "do": "lie@bed"            lying on the mattress (eyes open); "sleep@bed" eyes closed
    "do": "sit@chair"          seated on the chair, in profile, facing the desk/table next to it
    "do": "walkTo@oven"        walks to stand beside the oven
    "do": "place:phone@counter"  puts the phone down on the counter top (it stays there for the rest of the scene)
    "do": "pickup:phone@table"   takes it from the table
The pose is held across the following cuts of the scene until a "stand"/"walkTo"/"run" (coverage.py keeps it).
"""
import math

PERSON_M = 1.65          # a standing adult; the drawing is 720 units tall in a 400x800 box
FIG_UNITS = 720.0

# local anchor points per furniture piece (metres, before the piece's rotation/scale; y up)
POINTS = {
    "bed": {"top": (0, .68, .05), "head": (0, .68, -.92), "foot": (0, .68, .98)},
    "chair": {"seat": (0, .52, 0), "floor": (0, 0, 0), "facing": (0, 0, 1)},
    "desk": {"top": (0, .75, 0), "front": (0, .75, .38)},
    "table": {"top": (0, .77, 0), "front": (0, .77, .45)},
    "kitchen_counter": {"top": (0, .93, .05), "front": (0, .93, .32)},
    "shop_counter": {"top": (0, 1.06, 0), "front": (0, 1.06, .35)},
    "oven": {"top": (0, .93, 0), "front": (0, .45, .32)},
    "fridge": {"front": (0, 1.0, .36)},
    "bedside_table": {"top": (0, .57, 0)},
    "sofa": {"seat": (0, .45, .12), "facing": (0, 0, 1)},
    "tv": {"top": (0, .55, .1)},
    "bench": {"seat": (0, .49, 0), "facing": (0, 0, 1)},
    "bookshelf": {"front": (0, 1.0, .2)},
    "towel": {"top": (0, .05, 0), "head": (0, .05, -.8), "foot": (0, .05, .8)},
    "shelf_goods": {"front": (0, 1.0, .3)},
}
ALIAS = {"counter": ["kitchen_counter", "shop_counter"], "nightstand": ["bedside_table"], "bedside": ["bedside_table"],
         "couch": ["sofa"], "stove": ["oven"], "computer": ["desk"], "laptop": ["desk"], "seat": ["chair", "sofa", "bench"]}
FLOOR_OF = ("floor",)


def _rot(dx, dz, ry):
    c, s = math.cos(ry), math.sin(ry)
    return dx * c + dz * s, -dx * s + dz * c


class Cam:
    def __init__(self, cam, W, H):
        self.P = cam["pos"]; L = cam["look"]; self.W, self.H = W, H
        self.t = math.tan(math.radians(cam.get("fov", 40)) / 2)
        f = [L[i] - self.P[i] for i in range(3)]; n = math.sqrt(sum(v * v for v in f)); self.f = [v / n for v in f]
        r = [self.f[1] * 0 - self.f[2] * 1, self.f[2] * 0 - self.f[0] * 0, self.f[0] * 1 - self.f[1] * 0]   # f x up
        n = math.sqrt(sum(v * v for v in r)) or 1; self.r = [v / n for v in r]
        self.u = [self.r[1] * self.f[2] - self.r[2] * self.f[1], self.r[2] * self.f[0] - self.r[0] * self.f[2], self.r[0] * self.f[1] - self.r[1] * self.f[0]]

    def project(self, X):
        d = [X[i] - self.P[i] for i in range(3)]
        z = sum(d[i] * self.f[i] for i in range(3)); x = sum(d[i] * self.r[i] for i in range(3)); y = sum(d[i] * self.u[i] for i in range(3))
        z = max(z, 0.05); a = self.W / self.H
        return ((x / (z * self.t * a) + 1) / 2 * self.W, (1 - y / (z * self.t)) / 2 * self.H, z)

    def ppm(self, z):
        """screen pixels per metre at depth z"""
        return self.H / (2 * z * self.t)


def compute(setting, W, H):
    """setting = expanded setting dict (sets.expand done, furniture NOT yet expanded). -> {name: [anchor, ...]}"""
    cam = Cam(setting["camera"], W, H); out = {}
    for o in setting.get("objects", []):
        if o.get("t") != "furn":
            continue
        n = o.get("n"); pts = dict(POINTS.get(n, {})); pts.setdefault("floor", (0, 0, 0)); pts.setdefault("near", (0, 0, .9))
        s, ry = float(o.get("s", 1)), float(o.get("ry", 0)); bx, by, bz = float(o.get("x", 0)), float(o.get("y", 0)), float(o.get("z", 0))
        a = {"n": n}
        for k, (lx, ly, lz) in pts.items():
            dx, dz = _rot(lx * s, lz * s, ry)
            if k == "facing":    # a direction, not a point: which way the seat faces on screen (+1 right, -1 left)
                p0 = cam.project((bx, 0, bz)); p1 = cam.project((bx + dx, 0, bz + dz))
                a["face"] = 1 if p1[0] >= p0[0] else -1
                continue
            sx, sy, z = cam.project((bx + dx, by + ly * s, bz + dz))
            a[k] = [round(sx, 1), round(sy, 1)]
            if k in ("floor", "top", "seat", "foot"):
                a[k + "_ppm"] = round(cam.ppm(z), 2)
        fx, fy, _ = cam.project((bx, 0, bz)); a["on_screen"] = 0 <= fx <= W and 0 <= fy <= H * 1.05
        out.setdefault(n, []).append(a)
    # floor depth scale: screen y of a point on the floor -> pixels per metre there (so a person standing with feet
    # at that y is drawn at the right size for the set)
    L = setting["camera"]["look"]; P = setting["camera"]["pos"]; rows = []
    for k in range(60):
        z = P[2] - 1.2 - k * 0.6
        sx, sy, d = cam.project((L[0], 0, z))
        if 0 <= sy <= H * 1.3:
            rows.append([round(sy, 1), round(cam.ppm(d), 2)])
    out["_floor"] = sorted(rows)
    kind = setting.get("_kind") or {}
    if kind.get("type") == "street":    # cars come toward the camera in the left lane and drive away in the right one
        def pt(x, z):
            sx, sy, d = cam.project((x, 0, z)); return [round(sx, 1), round(sy, 1), round(cam.ppm(d), 2)]
        out["_lanes"] = [{"from": pt(-2.1, -55), "to": pt(-2.1, P[2] - 3)}, {"from": pt(2.1, P[2] - 4), "to": pt(2.1, -55), "away": True}]
        out["_walks"] = [{"from": pt(sx_, -40), "to": pt(sx_, P[2] - 3.5), "len_m": 40 + P[2]} for sx_ in (-5.6, 5.6)]
        out["_cross"] = pt(0, 3.0)[1]
        out["_pave"] = [[pt(sx_, z)[1], pt(sx_, z)[0], sx_] for sx_ in (-5.4, 5.4) for z in range(-40, int(P[2] - 2))]   # [y, x, side]
    if kind.get("type") == "beach":
        y0 = cam.project((0, 0, -16))[1]; y1 = cam.project((0, 0, -40))[1]
        out["_sea"] = {"y0": round(min(y0, y1), 1), "y1": round(max(y0, y1), 1), "ppm": round(cam.ppm(28), 2)}
    return out


def find(anchors, name, near_x=None):
    """the anchor for a name ("bed", "counter", ...): the on-screen one nearest near_x (or the most central)."""
    names = ALIAS.get(name, [name])
    cands = [a for n in names for a in (anchors or {}).get(n, [])]
    if not cands:
        return None
    vis = [a for a in cands if a.get("on_screen")] or cands
    ref = near_x if near_x is not None else None
    return min(vis, key=lambda a: abs(a["floor"][0] - ref) if ref is not None else -a.get("floor_ppm", 0))


def scale_at(ppm):
    """character scale s (400x800 drawing box) for a standing adult at a depth with ppm pixels per metre"""
    return round(PERSON_M * ppm / FIG_UNITS, 3)


def ppm_at_y(anchors, y):
    rows = (anchors or {}).get("_floor") or []
    if len(rows) < 2:
        return None
    if y <= rows[0][0]:
        return rows[0][1]
    for (y0, p0), (y1, p1) in zip(rows, rows[1:]):
        if y0 <= y <= y1:
            return p0 + (p1 - p0) * (y - y0) / max(1e-6, y1 - y0)
    return None          # below the nearest sampled floor point: leave the authored scale (foreground figures)
