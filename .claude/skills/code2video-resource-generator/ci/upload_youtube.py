"""Upload a rendered video to YouTube (Data API v3, resumable upload, no heavy client libraries: needs only `requests`).
python upload_youtube.py --video final.mp4 --meta metadata.json [--thumb thumb.jpg|thumb.png] [--confirm] [--allow-public]
Without --confirm it only validates and prints what WOULD be uploaded (dry run).
Secrets (environment): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN   (create once with get_refresh_token.py). Never printed.
metadata.json: {"title","description","tags":[...],"categoryId":"24","privacy":"private|unlisted|public","language":"vi","madeForKids":false,
                "publishAt":"2026-11-11T14:00:00Z" (optional: scheduled release; needs privacy private)}
Safety: default privacy is `private`; `public` is refused unless --allow-public is also given. The video is always flagged as containing
altered/synthetic media (AI voice + generated visuals), as YouTube policy asks.
Notes: an API project that has not passed YouTube's API audit can only upload as private; one upload costs ~1600 of the 10,000 daily quota units.
The night job does not call this directly: scripts/youtube_publish.py (repo root) builds the metadata from the publish pack and uses
token() / upload() / thumbnail() from here.
"""
import argparse, json, os, pathlib, re, sys

CHUNK = 8 * 1024 * 1024
SECRETS = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
THUMB_MAX = 2 * 1024 * 1024                         # thumbnails.set limit
THUMB_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def missing_secrets():
    return [k for k in SECRETS if not os.environ.get(k)]


def token():
    import requests
    miss = missing_secrets()
    if miss: raise RuntimeError("missing secret(s): " + ", ".join(miss))
    r = requests.post("https://oauth2.googleapis.com/token", data={"client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
                      "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=60)
    if r.status_code != 200:                         # the body names the OAuth error (invalid_grant...), never the secret values
        raise RuntimeError(f"token refresh failed: HTTP {r.status_code} {r.text[:200]}")
    return r.json()["access_token"]


def check_meta(m, allow_public):
    errs = []
    if not m.get("title") or len(m["title"]) > 100: errs.append("title missing or > 100 chars")
    if re.search(r"[<>]", m.get("title", "") + m.get("description", "")): errs.append("title/description may not contain < or > (YouTube rejects them)")
    if len(m.get("description", "")) > 5000: errs.append("description > 5000 chars")
    if len(",".join(m.get("tags", []))) > 450: errs.append("tags too long (< 500 chars total)")
    pv = m.get("privacy", "private")
    if pv not in ("private", "unlisted", "public"): errs.append("privacy must be private|unlisted|public")
    if pv == "public" and not allow_public: errs.append("privacy=public needs --allow-public (default is private)")
    if m.get("publishAt") and pv != "private": errs.append("publishAt (scheduled release) needs privacy=private")
    return errs


def body(m):
    lang = m.get("language", "vi")
    st = {"privacyStatus": m.get("privacy", "private"), "selfDeclaredMadeForKids": bool(m.get("madeForKids", False)), "containsSyntheticMedia": True}
    if m.get("publishAt"): st["publishAt"] = m["publishAt"]
    return {"snippet": {"title": m["title"], "description": m.get("description", ""), "tags": m.get("tags", []), "categoryId": str(m.get("categoryId", "24")),
                        "defaultLanguage": lang, "defaultAudioLanguage": lang}, "status": st}


def upload(video, m, access):
    import requests
    size = os.path.getsize(video)
    h = {"Authorization": f"Bearer {access}", "Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status", headers=h, data=json.dumps(body(m)), timeout=60)
    if r.status_code != 200: raise RuntimeError(f"videos.insert refused: HTTP {r.status_code} {r.text[:400]}")
    url = r.headers["Location"]; sent = 0
    with open(video, "rb") as f:
        while sent < size:
            f.seek(sent); chunk = f.read(CHUNK); end = sent + len(chunk) - 1
            rr = requests.put(url, headers={"Authorization": f"Bearer {access}", "Content-Length": str(len(chunk)), "Content-Range": f"bytes {sent}-{end}/{size}"}, data=chunk, timeout=600)
            if rr.status_code in (200, 201): return rr.json()
            if rr.status_code != 308: raise RuntimeError(f"upload chunk refused: HTTP {rr.status_code} {rr.text[:400]}")
            got = re.match(r"bytes=0-(\d+)", rr.headers.get("Range", ""))   # the server says how much it really kept
            sent = int(got.group(1)) + 1 if got else 0; print(f"uploaded {sent*100//size}%", flush=True)
    raise RuntimeError("upload ended without a final response")


def thumbnail(vid, thumb, access):
    """Returns the HTTP status (200 = set). Custom thumbnails need a verified channel; a failure here does not fail the upload."""
    import requests
    p = pathlib.Path(thumb); ctype = THUMB_TYPES.get(p.suffix.lower())
    if not ctype or p.stat().st_size > THUMB_MAX:
        print(f"thumbnail skipped: {p.name} must be jpg/png <= 2 MB"); return 0
    r = requests.post(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={vid}", headers={"Authorization": f"Bearer {access}", "Content-Type": ctype},
                      data=p.read_bytes(), timeout=120)
    print("thumbnail:", r.status_code, "" if r.status_code == 200 else r.text[:200]); return r.status_code


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--video", required=True); ap.add_argument("--meta", required=True); ap.add_argument("--thumb")
    ap.add_argument("--confirm", action="store_true"); ap.add_argument("--allow-public", action="store_true"); a = ap.parse_args()
    m = json.load(open(a.meta, encoding="utf-8")); errs = check_meta(m, a.allow_public)
    if not pathlib.Path(a.video).exists(): errs.append(f"video not found: {a.video}")
    if errs: sys.exit("metadata errors:\n  " + "\n  ".join(errs))
    print(f"{'UPLOAD' if a.confirm else 'DRY RUN'}: '{m['title']}' privacy={m.get('privacy', 'private')} size={os.path.getsize(a.video)/1e6:.1f} MB tags={len(m.get('tags', []))}")
    if not a.confirm: sys.exit(0)
    acc = token(); res = upload(a.video, m, acc); print("video id:", res["id"], "https://youtu.be/" + res["id"])
    if a.thumb: thumbnail(res["id"], a.thumb, acc)
    pathlib.Path("upload_result.json").write_text(json.dumps({"id": res["id"], "url": "https://youtu.be/" + res["id"], "privacy": m.get("privacy", "private")}))
