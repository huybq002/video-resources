"""Upload a rendered video to YouTube (Data API v3, resumable upload, no heavy client libraries: needs only `requests`).
python upload_youtube.py --video final.mp4 --meta metadata.json [--thumb thumb.jpg] [--confirm] [--allow-public]
Without --confirm it only validates and prints what WOULD be uploaded (dry run).
Secrets (environment): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN   (create once with get_refresh_token.py)
metadata.json: {"title","description","tags":[...],"categoryId":"24","privacy":"private|unlisted|public","language":"vi","madeForKids":false}
Safety: default privacy is `private`; `public` is refused unless --allow-public is also given. The video is always flagged as containing
altered/synthetic media (AI voice + generated visuals), as YouTube policy asks.
Notes: an API project that has not passed YouTube's API audit can only upload as private; one upload costs ~1600 of the 10,000 daily quota units.
"""
import argparse, json, os, pathlib, sys
import requests

CHUNK = 8 * 1024 * 1024

def token():
    r = requests.post("https://oauth2.googleapis.com/token", data={"client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
                      "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=60)
    r.raise_for_status(); return r.json()["access_token"]

def check_meta(m, allow_public):
    errs = []
    if not m.get("title") or len(m["title"]) > 100: errs.append("title missing or > 100 chars")
    if len(m.get("description", "")) > 5000: errs.append("description > 5000 chars")
    if len(",".join(m.get("tags", []))) > 450: errs.append("tags too long (< 500 chars total)")
    pv = m.get("privacy", "private")
    if pv not in ("private", "unlisted", "public"): errs.append("privacy must be private|unlisted|public")
    if pv == "public" and not allow_public: errs.append("privacy=public needs --allow-public (default is private)")
    return errs

def upload(video, m, access):
    body = {"snippet": {"title": m["title"], "description": m.get("description", ""), "tags": m.get("tags", []), "categoryId": str(m.get("categoryId", "24")),
                        "defaultLanguage": m.get("language", "vi"), "defaultAudioLanguage": m.get("language", "vi")},
            "status": {"privacyStatus": m.get("privacy", "private"), "selfDeclaredMadeForKids": bool(m.get("madeForKids", False)), "containsSyntheticMedia": True}}
    size = os.path.getsize(video)
    h = {"Authorization": f"Bearer {access}", "Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status", headers=h, data=json.dumps(body), timeout=60)
    r.raise_for_status(); url = r.headers["Location"]; sent = 0
    with open(video, "rb") as f:
        while sent < size:
            chunk = f.read(CHUNK); end = sent + len(chunk) - 1
            rr = requests.put(url, headers={"Content-Length": str(len(chunk)), "Content-Range": f"bytes {sent}-{end}/{size}"}, data=chunk, timeout=600)
            if rr.status_code in (200, 201): return rr.json()
            if rr.status_code != 308: rr.raise_for_status()
            sent = end + 1; print(f"uploaded {sent*100//size}%")
    raise RuntimeError("upload ended without a final response")

def thumbnail(vid, thumb, access):
    r = requests.post(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={vid}", headers={"Authorization": f"Bearer {access}", "Content-Type": "image/jpeg"}, data=open(thumb, "rb").read(), timeout=120)
    print("thumbnail:", r.status_code)      # needs a verified channel; a failure here does not fail the upload

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
