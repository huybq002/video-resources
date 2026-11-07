#!/usr/bin/env python3
"""Publish both cuts of a task (resource bundle + video) as one GitHub Release, and write outputs/<id>/manifest.json.

  python scripts/publish_release.py <id> --spec specs/<id>.json [--dry-run]

It looks for outputs/<id>/landscape (16:9) and outputs/<id>/portrait (9:16); a single
outputs/<id>/project is still accepted for older tasks. For each cut it attaches
<cut>-bundle.zip (the HyperFrames project incl. assets and voiceover.wav, without the video)
and <cut>.mp4, plus the shared thumbnails and metadata.json.

Needs GH_TOKEN (the workflow's GITHUB_TOKEN) unless --dry-run. Only the small manifest.json is
committed to git; download the release, then delete it if you wish.
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import zipfile

CUTS = [("landscape", "16:9"), ("portrait", "9:16")]
SKIP_IN_BUNDLE = {".mp4"}
MAX_ASSET_BYTES = 2_000_000_000


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def zip_bundle(project: pathlib.Path, target: pathlib.Path) -> pathlib.Path:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(project.rglob("*")):
            if f.is_file() and f.suffix.lower() not in SKIP_IN_BUNDLE and "node_modules" not in f.parts:
                z.write(f, f.relative_to(project).as_posix())
    return target


def find_video(project: pathlib.Path):
    return next((p for p in (project / "output.mp4", project / "final.mp4") if p.is_file()), None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--tag")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    out = pathlib.Path("outputs") / a.id
    spec = json.load(open(a.spec, encoding="utf-8"))
    found = [(name, aspect, out / name) for name, aspect in CUTS if (out / name).is_dir()]
    if not found and (out / "project").is_dir():
        found = [("project", spec.get("aspect", "16:9"), out / "project")]
    if not found:
        return sys.exit(f"no bundle at {out}/landscape, {out}/portrait or {out}/project")

    assets, cuts = [], []
    for name, aspect, project in found:
        video = find_video(project)
        if not video:
            return sys.exit(f"no output.mp4 / final.mp4 in {project}")
        bundle = zip_bundle(project, out / f"{name}-bundle.zip")
        named_video = out / f"{name}.mp4"
        if video.resolve() != named_video.resolve():
            named_video.write_bytes(video.read_bytes())
        assets += [named_video, bundle]
        cuts.append({"cut": name, "aspect": aspect, "video": named_video.name, "bundle": bundle.name})

    shared = [p for p in [out / "metadata.json", *sorted((out / "thumbnails").glob("*.png"))] if p.is_file()]
    assets += shared
    too_big = [p.name for p in assets if p.stat().st_size > MAX_ASSET_BYTES]
    if too_big:
        return sys.exit(f"asset(s) over 2 GB, GitHub Releases will reject them: {too_big}")

    tag = a.tag or f"{a.id}-{os.environ.get('GITHUB_RUN_ID', 'local')}"
    manifest = {
        "id": a.id, "tag": tag, "idea": spec.get("idea"), "lang": spec.get("lang"),
        "duration_s": spec.get("duration_s"), "cuts": cuts,
        "assets": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in assets],
        "release_url": None,
    }
    if not a.dry_run:
        notes = (f"{spec.get('idea', a.id)}\n\nduration {spec.get('duration_s')}s, lang {spec.get('lang')}.\n"
                 + "\n".join(f"- {c['cut']} ({c['aspect']}): `{c['video']}` + `{c['bundle']}`" for c in cuts)
                 + "\n\nEach *-bundle.zip is the HyperFrames project for that frame shape "
                   "(open with Code2Video Studio / hyperframes).")
        r = subprocess.run(["gh", "release", "create", tag, *map(str, assets), "--title", a.id, "--notes", notes],
                           capture_output=True, text=True)
        if r.returncode:
            return sys.exit("gh release failed:\n" + r.stderr[-600:])
        manifest["release_url"] = r.stdout.strip().splitlines()[-1]
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(("DRY RUN " if a.dry_run else "") + f"release {tag}: "
          + ", ".join(f"{x['name']} ({x['bytes'] / 1e6:.1f} MB)" for x in manifest["assets"]))
    print("manifest:", out / "manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
