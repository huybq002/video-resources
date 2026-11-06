#!/usr/bin/env python3
"""Publish the resource bundle + video of a task as a GitHub Release and write outputs/<id>/manifest.json.

  python scripts/publish_release.py <id> --spec specs/<id>.json [--video outputs/<id>/project/output.mp4] [--dry-run]

Assets: bundle.zip (the HyperFrames project incl. assets and voiceover.wav, without the video), the video,
thumbnails, metadata.json. Needs GH_TOKEN (the workflow's GITHUB_TOKEN) unless --dry-run.
Only the small manifest.json is committed to git; download the release, then delete it if you wish.
"""
import argparse, hashlib, json, os, pathlib, subprocess, sys, zipfile

ap = argparse.ArgumentParser(); ap.add_argument("id"); ap.add_argument("--spec", required=True); ap.add_argument("--video")
ap.add_argument("--tag"); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
out = pathlib.Path("outputs") / a.id; proj = out / "project"
if not proj.is_dir(): sys.exit(f"no bundle at {proj}")
video = pathlib.Path(a.video) if a.video else next((p for p in (proj / "output.mp4", proj / "final.mp4") if p.is_file()), None)
if not video or not video.is_file(): sys.exit("video not found (pass --video)")
spec = json.load(open(a.spec, encoding="utf-8"))
SKIP = {".mp4"}
bundle = out / "bundle.zip"
with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(proj.rglob("*")):
        if f.is_file() and f.suffix.lower() not in SKIP and "node_modules" not in f.parts:
            z.write(f, f.relative_to(proj).as_posix())
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()
extra = [p for p in [out / "metadata.json", *sorted((out / "thumbnails").glob("*.png"))] if p.is_file()]
assets = [video, bundle, *extra]
too_big = [p.name for p in assets if p.stat().st_size > 2_000_000_000]
if too_big: sys.exit(f"asset(s) over 2 GB, GitHub Releases will reject them: {too_big}")
tag = a.tag or f"{a.id}-{os.environ.get('GITHUB_RUN_ID', 'local')}"
manifest = {"id": a.id, "tag": tag, "idea": spec.get("idea"), "lang": spec.get("lang"), "duration_s": spec.get("duration_s"),
            "assets": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in assets], "release_url": None}
if not a.dry_run:
    notes = f"{spec.get('idea', a.id)}\n\nduration {spec.get('duration_s')}s, lang {spec.get('lang')}. bundle.zip = HyperFrames project (open with Code2Video Studio / hyperframes); {video.name} = rendered video."
    r = subprocess.run(["gh", "release", "create", tag, *map(str, assets), "--title", f"{a.id}", "--notes", notes], capture_output=True, text=True)
    if r.returncode: sys.exit("gh release failed:\n" + r.stderr[-600:])
    manifest["release_url"] = r.stdout.strip().splitlines()[-1]
(out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(("DRY RUN " if a.dry_run else "") + f"release {tag}: " + ", ".join(f"{x['name']} ({x['bytes']/1e6:.1f} MB)" for x in manifest["assets"]))
print("manifest:", out / "manifest.json")
