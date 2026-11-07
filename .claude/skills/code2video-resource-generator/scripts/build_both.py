"""One spec -> two finished projects, one per frame shape.

    python scripts/build_both.py <spec.json> <out_dir> [--series bible.json] [--check] [--only 16:9|9:16]

    <out_dir>/landscape/   16:9  1920x1080  (YouTube main)
    <out_dir>/portrait/    9:16  1080x1920  (Shorts / Reels / TikTok)

The two are NOT the same pixels cropped: each one is generated from scratch for its frame, so the
3D backgrounds are re-rendered by three.js at that resolution with the camera pulled back for
portrait, characters are scaled and re-placed, and the shot sizes (focus zoom) differ. The story,
the cast and `script.srt` are identical, which is what lets one voice-over serve both: make it in
`landscape/` and copy `voiceover.wav` + `timeline.json` into `portrait/` before rendering.

Exit code 1 if either build fails. Warnings from the spec lint are printed once per aspect.
"""
import argparse
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PY = sys.executable
ASPECTS = [("16:9", "landscape"), ("9:16", "portrait")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--series")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--skip-bg", action="store_true")
    ap.add_argument("--no-audio-tag", action="store_true")
    ap.add_argument("--only", choices=["16:9", "9:16"], help="build just one of them")
    a = ap.parse_args()

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    todo = [(asp, name) for asp, name in ASPECTS if not a.only or a.only == asp]
    made = []
    for i, (aspect, name) in enumerate(todo):
        target = out / name
        cmd = [PY, str(HERE / "generate.py"), str(a.spec), str(target), "--aspect", aspect]
        if a.series:
            cmd += ["--series", a.series]
            if i:                       # the first pass already wrote this episode into the bible
                cmd.append("--no-series-update")
        if a.check:
            cmd.append("--check")
        if a.skip_bg:
            cmd.append("--skip-bg")
        if a.no_audio_tag:
            cmd.append("--no-audio-tag")
        print(f"\n=== {aspect} -> {target}", flush=True)
        if subprocess.run(cmd).returncode:
            return 1
        made.append(target)
    print("\nbuilt: " + ", ".join(str(m) for m in made))
    if len(made) == 2:
        print("script.srt is identical in both: make voiceover.wav once in landscape/ and copy it "
              "(with timeline.json) into portrait/ before rendering.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
