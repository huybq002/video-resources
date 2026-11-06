from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Timeline


def _seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.3f}"


GSAP_CDN = "https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"

# Bảng màu bối cảnh, xoay vòng theo thứ tự scene để mỗi cảnh một không khí.
SCENE_PALETTES = [
    {"sky_top": "#1b2a4a", "sky_low": "#c45136", "ground": "#2a2320", "glow": "#f0a86b"},
    {"sky_top": "#0f3b34", "sky_low": "#3f8b74", "ground": "#12211d", "glow": "#d7f0c8"},
    {"sky_top": "#2b1a3d", "sky_low": "#7b4b9c", "ground": "#1a1224", "glow": "#e7c6ff"},
    {"sky_top": "#3a2a12", "sky_low": "#d98e3a", "ground": "#241a0e", "glow": "#ffe1a6"},
    {"sky_top": "#12283a", "sky_low": "#3a7ca6", "ground": "#0e1c28", "glow": "#bfe3ff"},
]


def _character_svg(flip: bool) -> str:
    mirror = " transform='scale(-1,1) translate(-100,0)'" if flip else ""
    return (
        "<svg viewBox='0 0 100 220' preserveAspectRatio='xMidYMid meet'>"
        f"<g{mirror} fill='#12100f'>"
        "<circle cx='50' cy='40' r='26'/>"
        "<path d='M50 66 C24 66 20 120 22 168 L34 168 L40 110 L46 168 L54 168 L60 110 L66 168 "
        "L78 168 C80 120 76 66 50 66 Z'/>"
        "</g></svg>"
    )


def _scene_document(scene, cues_in_scene, palette: dict) -> tuple[str, str]:
    """Trả về (tên file, nội dung) của một sub-composition scene (timeline relative 0..dur)."""
    comp_id = f"scene_{scene.scene_index}"
    dur = _seconds(max(1, scene.duration_ms))
    scene_start = scene.start_ms
    num_chars = 1 + (scene.scene_index % 2)
    positions = ["14%"] if num_chars == 1 else ["12%", "66%"]

    chars_html, caps_html, anim_chars, anim_caps = [], [], [], []
    for ci in range(num_chars):
        cid = f"ch-{scene.scene_index}-{ci}"
        chars_html.append(
            f"<div id='{cid}' class='character' style='left:{positions[ci]}'>"
            f"{_character_svg(flip=(ci % 2 == 1))}</div>"
        )
        anim_chars.append(
            {
                "id": cid,
                "enter": round(0.15 * ci, 3),
                "from": -70 + ci * 140,
                "floatStart": round(0.9 + 0.15 * ci, 3),
                "floatDur": round(max(0.5, float(dur) - 1.2), 3),
            }
        )
    for cue in cues_in_scene:
        cap_id = f"cap-{cue.index}"
        local_start = (cue.start_ms - scene_start) / 1000
        local_dur = max(0.15, cue.duration_ms / 1000)
        caps_html.append(
            f"<div id='{cap_id}' class='caption'><span>{html.escape(cue.text)}</span></div>"
        )
        anim_caps.append({"id": cap_id, "start": round(local_start, 3), "dur": round(local_dur, 3)})

    scene_data = json.dumps(
        {"bg": "bg", "dur": float(dur), "chars": anim_chars, "caps": anim_caps},
        ensure_ascii=False,
    ).replace("</", "<\\/")

    style = f"""
    [data-composition-id='{comp_id}'] {{ position: absolute; inset: 0; overflow: hidden;
      font-family: Arial, sans-serif; }}
    [data-composition-id='{comp_id}'] .background {{ position: absolute; inset: -8%; z-index: 1;
      background: linear-gradient(180deg, var(--sky-top) 0%, var(--sky-low) 62%, var(--ground) 62%, var(--ground) 100%); }}
    [data-composition-id='{comp_id}'] .background::after {{ content: ''; position: absolute; left: 50%; top: 40%;
      width: 40%; height: 40%; transform: translate(-50%, -50%); border-radius: 50%;
      background: radial-gradient(circle, var(--glow) 0%, transparent 70%); opacity: .5; }}
    [data-composition-id='{comp_id}'] .horizon {{ position: absolute; left: 0; right: 0; top: 62%; height: 2px; z-index: 2;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,.35), transparent); }}
    [data-composition-id='{comp_id}'] .character {{ position: absolute; bottom: 16%; width: 16%; height: 52%; z-index: 3; opacity: 0; }}
    [data-composition-id='{comp_id}'] .character svg {{ width: 100%; height: 100%; display: block;
      filter: drop-shadow(0 18px 24px rgba(0,0,0,.45)); }}
    [data-composition-id='{comp_id}'] .caption {{ position: absolute; left: 8%; right: 8%; bottom: 11%; z-index: 4;
      display: grid; place-items: center; text-align: center; opacity: 0; }}
    [data-composition-id='{comp_id}'] .caption span {{ max-width: 1400px; padding: 18px 34px; border-radius: 14px;
      background: rgba(13,18,17,.62); color: #f4efe6; font-size: 60px; line-height: 1.25; font-weight: 700; }}
    """

    script = f"""
    (function () {{
      const d = {scene_data};
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo("[data-composition-id='{comp_id}'] .background", {{ scale: 1.04 }},
        {{ scale: 1.12, duration: d.dur, ease: "none" }}, 0);
      for (const ch of d.chars) {{
        const sel = "#" + ch.id;
        tl.fromTo(sel, {{ opacity: 0, x: ch.from, y: 30 }},
          {{ opacity: 1, x: 0, y: 0, duration: 0.6, ease: "power2.out" }}, ch.enter);
        tl.fromTo(sel, {{ y: 0 }}, {{ y: -14, duration: ch.floatDur, ease: "sine.inOut" }}, ch.floatStart);
      }}
      for (const cap of d.caps) {{
        const sel = "#" + cap.id;
        tl.fromTo(sel, {{ opacity: 0, y: 24 }},
          {{ opacity: 1, y: 0, duration: 0.28, ease: "power2.out" }}, cap.start);
        tl.to(sel, {{ opacity: 0, duration: 0.2 }}, cap.start + Math.max(0.3, cap.dur - 0.2));
      }}
      window.__timelines = window.__timelines || {{}};
      window.__timelines['{comp_id}'] = tl;
    }})();
    """

    document = (
        f"<template id='{comp_id}-template'>\n"
        f"  <div data-composition-id='{comp_id}' data-width='1920' data-height='1080' data-duration='{dur}' "
        f"style='--sky-top:{palette['sky_top']};--sky-low:{palette['sky_low']};"
        f"--ground:{palette['ground']};--glow:{palette['glow']};'>\n"
        f"    <div class='background'></div>\n    <div class='horizon'></div>\n"
        f"    {''.join(chars_html)}\n    {''.join(caps_html)}\n"
        f"    <style>{style}</style>\n"
        f"    <script src='{GSAP_CDN}'></script>\n"
        f"    <script>{script}</script>\n"
        f"  </div>\n</template>\n"
    )
    return f"{comp_id}.html", document


def _root_document(timeline: Timeline, hosts: list[str]) -> str:
    root_duration = _seconds(timeline.duration_ms)
    audio_name = html.escape(timeline.audio, quote=True)
    return f"""<!doctype html>
<html lang='vi'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=1920, height=1080'>
  <title>Code2Video composition</title>
  <script src='{GSAP_CDN}'></script>
  <style>
    html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #0d1211; }}
    #root {{ position: relative; width: 1920px; height: 1080px; overflow: hidden; }}
    #voice {{ position: absolute; width: 1px; height: 1px; opacity: 0; }}
    .scene-host {{ position: absolute; inset: 0; }}
  </style>
</head>
<body>
  <div id='root' data-composition-id='code2video' data-width='1920' data-height='1080'
       data-start='0' data-duration='{root_duration}'>
    <audio id='voice' src='{audio_name}' data-start='0' data-duration='{root_duration}' data-track-index='0'></audio>
    {''.join(hosts)}
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines = window.__timelines || {{}};
      window.__timelines['code2video'] = tl;
    </script>
  </div>
</body>
</html>
"""


_HYPERFRAMES_JSON = json.dumps(
    {
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
        "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
        "media": {"autoProxy": True},
    },
    indent=2,
)


def _package_json(name: str) -> str:
    return json.dumps(
        {
            "name": name,
            "private": True,
            "type": "module",
            "scripts": {
                "dev": "npx --yes hyperframes preview",
                "check": "npx --yes hyperframes check",
                "render": "npx --yes hyperframes render",
            },
        },
        indent=2,
    )


def render_composition(timeline: Timeline, output_path: Path) -> Path:
    project_dir = output_path.parent
    compositions_dir = project_dir / "compositions"
    compositions_dir.mkdir(parents=True, exist_ok=True)

    cues_by_index = {cue.index: cue for cue in timeline.cues}
    hosts: list[str] = []
    for position, scene in enumerate(timeline.scenes):
        lo, hi = scene.cue_range
        cues_in_scene = [cues_by_index[i] for i in range(lo, hi + 1) if i in cues_by_index]
        palette = SCENE_PALETTES[position % len(SCENE_PALETTES)]
        comp_id = f"scene_{scene.scene_index}"
        filename, document = _scene_document(scene, cues_in_scene, palette)
        (compositions_dir / filename).write_text(document, encoding="utf-8")
        hosts.append(
            f"<div id='{comp_id}-host' class='scene-host clip' data-composition-id='{comp_id}' "
            f"data-composition-src='compositions/{filename}' data-start='{_seconds(scene.start_ms)}' "
            f"data-duration='{_seconds(max(1, scene.duration_ms))}' data-track-index='{scene.scene_index}'></div>"
        )

    (project_dir / "index.html").write_text(_root_document(timeline, hosts), encoding="utf-8")
    (project_dir / "hyperframes.json").write_text(_HYPERFRAMES_JSON, encoding="utf-8")
    (project_dir / "package.json").write_text(_package_json(project_dir.name or "code2video"), encoding="utf-8")
    (project_dir / "meta.json").write_text(
        json.dumps(
            {
                "id": project_dir.name,
                "name": project_dir.name,
                "createdAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_path
