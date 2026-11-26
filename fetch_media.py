"""내 인스타 최근 게시물 목록을 받아 앞쪽 N개를 fetched/ 에 내려받는다 (게시는 하지 않음)."""
import json, os, requests
tok = os.environ["IG_TOKEN"]
host = "https://graph.instagram.com/v22.0" if tok.startswith("IG") else "https://graph.facebook.com/v22.0"
me = "/me" if tok.startswith("IG") else "/17841445606722579"
F = "id,media_type,media_url,thumbnail_url,permalink,timestamp,caption,children{media_type,media_url,thumbnail_url}"
d = requests.get(f"{host}{me}/media", params={"fields": F, "limit": 9, "access_token": tok}, timeout=60).json()
os.makedirs("fetched", exist_ok=True)
index = []
for n, m in enumerate(d.get("data", []), 1):
    items = (m.get("children") or {}).get("data") or [m]
    files = []
    for k, c in enumerate(items, 1):
        url = c.get("media_url") if c.get("media_type") != "VIDEO" else c.get("thumbnail_url") or c.get("media_url")
        ext = "mp4" if c.get("media_type") == "VIDEO" else "jpg"
        p = f"fetched/{n:02d}_{k:02d}.{ext}"
        open(p, "wb").write(requests.get(url, timeout=120).content)
        files.append(p)
        if c.get("media_type") == "VIDEO" and c.get("thumbnail_url"):
            q = f"fetched/{n:02d}_{k:02d}_thumb.jpg"; open(q, "wb").write(requests.get(c["thumbnail_url"], timeout=60).content); files.append(q)
    index.append({"순서": n, "id": m["id"], "type": m["media_type"], "permalink": m.get("permalink"),
                  "timestamp": m.get("timestamp"), "caption_첫줄": (m.get("caption") or "").split("\n")[0], "files": files})
json.dump(index, open("fetched/index.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(index, ensure_ascii=False, indent=1) if index else d)
