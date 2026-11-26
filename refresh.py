"""토큰 연장기. 매주 실행해 Threads / Instagram 토큰을 새 60일짜리로 바꾸고 금고에 다시 저장한다.

Threads 토큰이 1시간짜리(처음 받은 토큰)면 앱 시크릿으로 60일짜리로 바꾼다.
새 토큰은 화면에 출력하지 않고, gh 명령으로 금고에만 넣는다.
"""
import os
import subprocess
import sys

import requests


def get(url, **params):
    r = requests.get(url, params=params, timeout=60)
    d = r.json()
    if r.status_code >= 400 or "access_token" not in d:
        raise RuntimeError(f"{url} -> {r.status_code}: {d.get('error', d)}")
    return d


def save(name, value):
    subprocess.run(["gh", "secret", "set", name, "--repo", os.environ["REPO"]],
                   input=value.encode(), check=True)


ok = True
th = os.environ.get("THREADS_TOKEN")
if th:
    try:
        d = get("https://graph.threads.net/refresh_access_token", grant_type="th_refresh_token", access_token=th)
    except Exception as e1:
        try:
            d = get("https://graph.threads.net/access_token", grant_type="th_exchange_token",
                    client_secret=os.environ["THREADS_APP_SECRET"], access_token=th)
        except Exception as e2:
            ok = False
            d = None
            print(f"[Threads] 연장 실패: {e1} / {e2}", file=sys.stderr)
    if d:
        save("THREADS_TOKEN", d["access_token"])
        print(f"[Threads] 연장 완료, {int(d.get('expires_in', 0)) // 86400}일 유효")

ig = os.environ.get("IG_TOKEN")
if ig:
    try:
        d = get("https://graph.instagram.com/refresh_access_token", grant_type="ig_refresh_token", access_token=ig)
        save("IG_TOKEN", d["access_token"])
        print(f"[Instagram] 연장 완료, {int(d.get('expires_in', 0)) // 86400}일 유효")
    except Exception as e:
        ok = False
        print(f"[Instagram] 연장 실패: {e}", file=sys.stderr)

sys.exit(0 if ok else 1)
