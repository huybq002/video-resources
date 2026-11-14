"""Event relay lint: does the picture hand the stage to a new main visual, or only re-frame the same one?

See references/event-relay.md. relay(spec) -> WARNING lines.
"""


def _cues(spec):
    """per scene: [(effective setting, actors tuple, shot kind, has_new_lead)] in order"""
    out = {}
    for sc in spec.get("scenes", []):
        rows = []
        cur = None
        for item in sc.get("shots", []):
            seq = item.get("sequence") or {}
            if seq:
                cur = cur or (list(seq.get("settings", [])) + [seq.get("setting")] + [None])[0]
                actors = tuple(sorted(a.get("k", "") for a in seq.get("actors", []) if isinstance(a, dict)))
                if seq.get("setting") and not seq.get("settings"):
                    cur = seq["setting"]
                lines = seq.get("cues", []) or seq.get("lines", [])
                for c in lines:
                    if not isinstance(c, dict):
                        rows.append((cur, actors, "medium", False)); continue
                    if c.get("at"): cur = c["at"]
                    on = tuple(sorted(c.get("on", []) or [])) or actors
                    kind = c.get("shot", "medium")
                    lead = bool(c.get("props") or c.get("hud") or c.get("do") or c.get("at") or kind in ("insert", "establish", "ots", "two", "reaction")
                                or c.get("who") and c.get("who") != "narrator")
                    rows.append((cur, on, kind, lead))
            else:
                cur = item.get("setting") or cur
                actors = tuple(sorted(a.get("k", "") for a in item.get("actors", []) if isinstance(a, dict)))
                rows.append((cur, actors, item.get("shot", "medium"), bool(item.get("props") or item.get("overlays") or item.get("do"))))
        out[sc.get("id")] = (rows, float(sc.get("target_s", 0) or 0))
    return out


def relay(spec):
    notes = []
    scenes = _cues(spec)
    n_scenes = len(scenes)
    for sid, (rows, target) in scenes.items():
        # 4+ in a row on the same stage with nothing new leading
        run = 1
        for i in range(1, len(rows)):
            same = rows[i][:3] == rows[i - 1][:3] and not rows[i][3]
            run = run + 1 if same else 1
            if run == 4:
                notes.append(f"WARNING: relay: scene {sid}: lines {i - 2}-{i + 1} are the same place, same people and same shot with "
                             f"nothing new leading: that is one picture re-framed, not a handoff. Give a line a new lead "
                             f"(insert of the object, a `hud`, an action, another person or place); references/event-relay.md")
                break
        places = {r[0] for r in rows}
        actors = {r[1] for r in rows}
        if n_scenes >= 3 and target >= 15 and len(rows) >= 4 and len(places) == 1 and len(actors) == 1 \
                and sum(1 for r in rows if r[3]) < max(2, len(rows) // 3):
            notes.append(f"WARNING: relay: scene {sid} ({target:.0f}s) stays on one place with one actor and almost nothing "
                         f"new leads the picture ({sum(1 for r in rows if r[3])} of {len(rows)} lines): change the stage mid-scene")
    return notes
