"""SCHEMA SNS 자동 게시기.

queue.yaml 에 적힌 게시물 중 게시 시각(KST)이 된 것을 Threads / Instagram API 로 올리고,
결과를 state.json 에 기록한다. GitHub Actions 가 10분마다 실행한다.

환경 변수
  THREADS_TOKEN, IG_TOKEN  : 금고(Secrets)에서 들어오는 토큰
  REPO                     : owner/name (이미지 공개 주소를 만들 때 사용)
  DRY_RUN=1                : 실제로 올리지 않고 무엇을 올릴지만 출력
  ONLY_ID=<id>             : 그 게시물 하나만 (시각 무시) 처리. 테스트용
"""
import json
import os
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
import yaml

KST = ZoneInfo("Asia/Seoul")
GRACE = timedelta(hours=3)  # 이보다 늦게 발견한 게시물은 올리지 않고 'missed' 로 남긴다
TH = "https://graph.threads.net/v1.0"
IG = "https://graph.instagram.com/v22.0"

DRY = os.environ.get("DRY_RUN") == "1"
ONLY = os.environ.get("ONLY_ID", "").strip()
REPO = os.environ.get("REPO", "")
BRANCH = os.environ.get("BRANCH", "main")


def media_url(path: str) -> str:
    path = path.lstrip("/")
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/" + urllib.parse.quote(path)


def call(method, url, **params):
    r = requests.request(method, url, params=params, timeout=60)
    try:
        data = r.json()
    except ValueError:
        data = {"raw": r.text[:500]}
    if r.status_code >= 400 or "error" in data:
        msg = data.get("error", data)
        raise RuntimeError(f"{method} {url.split('?')[0]} -> {r.status_code}: {msg}")
    return data


# ---------------- Threads ----------------
def th_wait(cid, token):
    for _ in range(30):
        s = call("GET", f"{TH}/{cid}", fields="status,error_message", access_token=token)
        if s.get("status") == "FINISHED":
            return
        if s.get("status") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Threads 컨테이너 실패: {s}")
        time.sleep(5)
    raise RuntimeError("Threads 컨테이너 처리 시간 초과")


def th_container(token, text, images, reply_to=None, topic_tag=None):
    base = {"access_token": token}
    if reply_to:
        base["reply_to_id"] = reply_to
    if topic_tag:
        base["topic_tag"] = topic_tag
    if not images:
        return call("POST", f"{TH}/me/threads", media_type="TEXT", text=text, **base)["id"]
    if len(images) == 1:
        cid = call("POST", f"{TH}/me/threads", media_type="IMAGE",
                   image_url=media_url(images[0]), text=text, **base)["id"]
        th_wait(cid, token)
        return cid
    kids = []
    for p in images[:20]:
        k = call("POST", f"{TH}/me/threads", media_type="IMAGE", is_carousel_item="true",
                 image_url=media_url(p), access_token=token)["id"]
        kids.append(k)
    for k in kids:
        th_wait(k, token)
    cid = call("POST", f"{TH}/me/threads", media_type="CAROUSEL",
               children=",".join(kids), text=text, **base)["id"]
    th_wait(cid, token)
    return cid


def th_publish(token, cid):
    return call("POST", f"{TH}/me/threads_publish", creation_id=cid, access_token=token)["id"]


def post_threads(item, token, ids):
    parts = [{"text": item.get("text", ""), "images": item.get("images", [])}] + item.get("replies", [])
    parent = None
    for i, part in enumerate(parts):
        text = part.get("text", "")
        if len(text) > 500:
            raise RuntimeError(f"{item['id']} 의 {i}번째 글이 500자를 넘음 ({len(text)}자)")
        cid = th_container(token, text, part.get("images", []), reply_to=parent,
                           topic_tag=item.get("topic_tag") if i == 0 else None)
        pid = th_publish(token, cid)
        ids.append(pid)
        parent = pid  # 답글은 바로 앞 글에 이어 단다 (타래)
        time.sleep(3)
    return ids


# ---------------- Instagram ----------------
def ig_wait(cid, token):
    for _ in range(40):
        s = call("GET", f"{IG}/{cid}", fields="status_code,status", access_token=token)
        if s.get("status_code") == "FINISHED":
            return
        if s.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram 컨테이너 실패: {s}")
        time.sleep(5)
    raise RuntimeError("Instagram 컨테이너 처리 시간 초과")


def post_instagram(item, token):
    images = item.get("images", [])
    caption = item.get("text", "")
    if item.get("video"):  # 릴스
        params = {"media_type": "REELS", "video_url": media_url(item["video"]), "caption": caption,
                  "share_to_feed": "true", "access_token": token}
        if item.get("cover"):
            params["cover_url"] = media_url(item["cover"])
        cid = call("POST", f"{IG}/me/media", **params)["id"]
        ig_wait(cid, token)
        return [call("POST", f"{IG}/me/media_publish", creation_id=cid, access_token=token)["id"]]
    if not images:
        raise RuntimeError("인스타 게시물에는 이미지가 1장 이상 필요")
    if len(caption) > 2200:
        raise RuntimeError("인스타 캡션이 2200자를 넘음")
    if len(images) == 1:
        cid = call("POST", f"{IG}/me/media", image_url=media_url(images[0]),
                   caption=caption, access_token=token)["id"]
    else:
        kids = []
        for p in images[:10]:
            kids.append(call("POST", f"{IG}/me/media", image_url=media_url(p),
                             is_carousel_item="true", access_token=token)["id"])
        for k in kids:
            ig_wait(k, token)
        cid = call("POST", f"{IG}/me/media", media_type="CAROUSEL", children=",".join(kids),
                   caption=caption, access_token=token)["id"]
    ig_wait(cid, token)
    return [call("POST", f"{IG}/me/media_publish", creation_id=cid, access_token=token)["id"]]


# ---------------- main ----------------
def main():
    queue = yaml.safe_load(open("queue.yaml", encoding="utf-8")) or []
    try:
        state = json.load(open("state.json", encoding="utf-8"))
    except FileNotFoundError:
        state = {}
    now = datetime.now(KST)
    failed = False
    for item in queue:
        iid = item["id"]
        if ONLY and iid != ONLY:
            continue
        if not ONLY:
            if item.get("hold"):
                continue
            st = state.get(iid, {})
            if st.get("status") in ("posted", "missed", "partial"):
                continue
            if st.get("status") == "error" and st.get("tries", 0) >= 3:
                continue
            at = datetime.strptime(str(item["at"]), "%Y-%m-%d %H:%M").replace(tzinfo=KST)
            if at > now:
                continue
            if now - at > GRACE:
                state[iid] = {"status": "missed", "at": item["at"], "checked": now.isoformat()}
                print(f"[MISSED] {iid} ({item['at']}) - 너무 늦어서 올리지 않음")
                continue
        ch = item["channel"]
        print(f"[DUE] {iid} -> {ch} ({item.get('at')})")
        if DRY:
            print(json.dumps(item, ensure_ascii=False, indent=1)[:1500])
            continue
        ids = []
        try:
            if ch == "threads":
                post_threads(item, os.environ["THREADS_TOKEN"], ids)
            elif ch == "instagram":
                ids = post_instagram(item, os.environ["IG_TOKEN"])
            else:
                raise RuntimeError(f"모르는 채널: {ch}")
            state[iid] = {"status": "posted", "ids": ids, "posted_at": datetime.now(KST).isoformat()}
            print(f"[OK] {iid} -> {ids}")
        except Exception as e:  # 하나가 실패해도 나머지는 계속
            failed = True
            prev = state.get(iid, {})
            state[iid] = {"status": "partial" if ids else "error", "ids": ids, "error": str(e)[:500],
                          "tries": prev.get("tries", 0) + 1, "last_try": datetime.now(KST).isoformat()}
            print(f"[ERROR] {iid}: {e}", file=sys.stderr)
    json.dump(state, open("state.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
