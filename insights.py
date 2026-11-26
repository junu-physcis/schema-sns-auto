"""성과 수집기. 매일 아침 state.json에 posted로 기록된 게시물의 수치를 모아 성과/ 폴더에 저장한다.
- 성과/YYYY-MM-DD.json : 날짜별 원본
- 성과/latest.md        : 총괄팀이 읽는 표
지원 안 되는 항목은 비워 둔다. 토큰은 출력하지 않는다.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import requests
import yaml

KST = timezone(timedelta(hours=9))
TH = "https://graph.threads.net/v1.0"
IG = "https://graph.instagram.com/v22.0"


def get(url, **p):
    try:
        r = requests.get(url, params=p, timeout=60)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def metrics(d):
    out = {}
    for m in d.get("data", []) or []:
        v = m.get("values", [{}])
        out[m["name"]] = (m.get("total_value") or {}).get("value", v[-1].get("value") if v else None)
    return out


def main():
    th, ig = os.environ.get("THREADS_TOKEN"), os.environ.get("IG_TOKEN")
    state = json.load(open("state.json", encoding="utf-8")) if os.path.exists("state.json") else {}
    queue = {i["id"]: i for i in yaml.safe_load(open("queue.yaml", encoding="utf-8"))}
    now = datetime.now(KST)
    rep = {"collected_at": now.isoformat(), "account": {}, "posts": {}}

    if th:
        u = metrics(get(f"{TH}/me/threads_insights", metric="followers_count,views,likes,replies,reposts,quotes",
                        access_token=th))
        rep["account"]["threads"] = u
    if ig:
        me = get(f"{IG}/me", fields="followers_count,media_count", access_token=ig)
        rep["account"]["instagram"] = {k: me.get(k) for k in ("followers_count", "media_count")}

    for iid, st in state.items():
        if st.get("status") not in ("posted", "partial") or not st.get("ids"):
            continue
        item = queue.get(iid, {})
        ch = item.get("channel", "threads" if iid.startswith("th") else "instagram")
        first = st["ids"][0]
        row = {"channel": ch, "slot": item.get("slot"), "at": item.get("at"), "posted_at": st.get("posted_at")}
        if ch == "threads" and th:
            row.update(metrics(get(f"{TH}/{first}/insights", metric="views,likes,replies,reposts,quotes,shares",
                                   access_token=th)))
            # 타래 전체 답글 수(우리 답글 제외 전) 참고용
            conv = get(f"{TH}/{first}/conversation", fields="id,username", access_token=th)
            others = [c for c in conv.get("data", []) or [] if c.get("username") != "junu_physics"]
            row["외부답글"] = len(others)
        elif ch == "instagram" and ig:
            row.update(metrics(get(f"{IG}/{first}/insights",
                                   metric="reach,views,likes,comments,shares,saved,follows,total_interactions",
                                   access_token=ig)))
        rep["posts"][iid] = row

    os.makedirs("성과", exist_ok=True)
    json.dump(rep, open(f"성과/{now:%Y-%m-%d}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    cols = ["views", "reach", "likes", "replies", "comments", "reposts", "quotes", "shares", "saved", "follows", "외부답글"]
    lines = [f"# 성과 ({now:%Y-%m-%d %H:%M} KST 수집)", ""]
    for ch, v in rep["account"].items():
        lines.append(f"- {ch} 계정: " + ", ".join(f"{k} {x}" for k, x in v.items()))
    lines += ["", "| ID | 채널 | slot | 예약시각 | " + " | ".join(cols) + " |",
              "|" + "---|" * (4 + len(cols))]
    for iid, r in rep["posts"].items():
        lines.append(f"| {iid} | {r['channel']} | {r.get('slot') or ''} | {r.get('at') or ''} | "
                     + " | ".join("" if r.get(c) is None else str(r.get(c)) for c in cols) + " |")
    lines += ["", "빈칸 = 그 채널에서 지원 안 하는 항목. shares = 보내기(공유)."]
    open("성과/latest.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


main()
