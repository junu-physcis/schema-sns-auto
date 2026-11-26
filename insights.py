"""성과 수집기. 계정의 최근 게시물(자동 게시 + 앱에서 직접 올린 것 모두)을 미디어 목록에서 읽어 수치를 모은다.
- 성과/YYYY-MM-DD_HHMM.json : 수집 시점별 원본
- 성과/latest.md            : 총괄팀이 읽는 표
지원 안 되는 항목은 비워 둔다. 토큰은 출력하지 않는다.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import requests
import yaml

KST = timezone(timedelta(hours=9))
TH = "https://graph.threads.net/v1.0"
IG_USER_ID = "17841445606722579"


def ig_host(t):
    return "https://graph.instagram.com/v22.0" if t.startswith("IG") else "https://graph.facebook.com/v22.0"


def ig_me(t):
    return ig_host(t) + ("/me" if t.startswith("IG") else f"/{IG_USER_ID}")


def get(url, **p):
    try:
        return requests.get(url, params=p, timeout=60).json()
    except Exception as e:
        return {"error": str(e)}


def metrics(d):
    out = {}
    for m in d.get("data", []) or []:
        v = m.get("values", [{}])
        out[m["name"]] = (m.get("total_value") or {}).get("value", v[-1].get("value") if v else None)
    return out


def insights(url, names, tok):
    """한 번에 요청하고, 지원 안 되는 항목이 섞여 실패하면 하나씩 다시 요청한다."""
    d = get(url, metric=",".join(names), access_token=tok)
    if "error" not in d:
        return metrics(d)
    out = {}
    for n in names:
        out.update(metrics(get(url, metric=n, access_token=tok)))
    return out


def kst(ts):
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").astimezone(KST).strftime("%m/%d %H:%M")
    except Exception:
        return ts or ""


def main():
    th, ig = os.environ.get("THREADS_TOKEN"), os.environ.get("IG_TOKEN")
    state = json.load(open("state.json", encoding="utf-8")) if os.path.exists("state.json") else {}
    queue = {i["id"]: i for i in yaml.safe_load(open("queue.yaml", encoding="utf-8"))}
    id2q = {}
    for qid, st in state.items():
        for k, mid in enumerate(st.get("ids") or []):
            id2q.setdefault(mid, qid if k == 0 else f"{qid}(답글)")
    now = datetime.now(KST)
    rep = {"collected_at": now.isoformat(), "account": {}, "posts": []}

    if th:
        rep["account"]["threads"] = insights(f"{TH}/me/threads_insights",
                                             ["followers_count", "views", "likes", "replies", "reposts", "quotes"], th)
        lst = get(f"{TH}/me/threads", fields="id,timestamp,text,permalink,media_type", limit=25, access_token=th)
        for m in lst.get("data", []) or []:
            row = {"채널": "threads", "예약ID": id2q.get(m["id"], "(직접 게시)"), "게시": kst(m.get("timestamp")),
                   "첫줄": (m.get("text") or "").split("\n")[0][:30], "link": m.get("permalink")}
            row.update(insights(f"{TH}/{m['id']}/insights", ["views", "likes", "replies", "reposts", "quotes", "shares"], th))
            rep["posts"].append(row)
    if ig:
        me = get(ig_me(ig), fields="followers_count,media_count", access_token=ig)
        rep["account"]["instagram"] = {k: me.get(k) for k in ("followers_count", "media_count")}
        lst = get(f"{ig_me(ig)}/media", fields="id,timestamp,caption,permalink,media_type,media_product_type", limit=15,
                  access_token=ig)
        for m in lst.get("data", []) or []:
            reel = m.get("media_product_type") == "REELS"
            names = ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions"] + ([] if reel else ["follows", "profile_visits"])
            row = {"채널": "instagram" + (" 릴스" if reel else ""), "예약ID": id2q.get(m["id"], "(직접 게시)"),
                   "게시": kst(m.get("timestamp")), "첫줄": (m.get("caption") or "").split("\n")[0][:30], "link": m.get("permalink")}
            row.update(insights(f"{ig_host(ig)}/{m['id']}/insights", names, ig))
            rep["posts"].append(row)

    os.makedirs("성과", exist_ok=True)
    json.dump(rep, open(f"성과/{now:%Y-%m-%d_%H%M}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    cols = ["views", "reach", "likes", "replies", "comments", "reposts", "quotes", "shares", "saved", "follows", "profile_visits"]
    lines = [f"# 성과 ({now:%Y-%m-%d %H:%M} KST 수집)", ""]
    for ch, v in rep["account"].items():
        lines.append(f"- {ch} 계정: " + ", ".join(f"{k} {x}" for k, x in v.items()))
    lines += ["", "| 채널 | 예약ID | 게시 | 첫 줄 | " + " | ".join(cols) + " |", "|" + "---|" * (4 + len(cols))]
    for r in rep["posts"]:
        lines.append(f"| {r['채널']} | {r['예약ID']} | {r['게시']} | {r['첫줄'].replace('|', '/')} | "
                     + " | ".join("" if r.get(c) is None else str(r.get(c)) for c in cols) + " |")
    lines += ["", "빈칸 = 그 채널·형식에서 지원 안 하는 항목. shares = 보내기(공유), saved = 저장, follows = 그 게시물로 생긴 팔로우.",
              "스레드는 답글도 각각 한 줄로 나온다(예약ID 뒤 '(답글)')."]
    open("성과/latest.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


main()
