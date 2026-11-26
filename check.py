"""토큰 점검기. 글은 올리지 않고, 각 토큰으로 내 계정 이름만 조회해 본다. 토큰 값은 출력하지 않는다."""
import os
import sys

import requests

ok = True
for name, url, fields in [
    ("THREADS_TOKEN", "https://graph.threads.net/v1.0/me", "id,username"),
    ("IG_TOKEN", None, "username,followers_count"),
]:
    tok = os.environ.get(name)
    if not tok:
        print(f"[{name}] 금고에 없음")
        continue
    if url is None:
        url = "https://graph.instagram.com/v22.0/me" if tok.startswith("IG") else "https://graph.facebook.com/v22.0/17841445606722579"
        print(f"[{name}] 토큰 종류: {'인스타 로그인' if tok.startswith('IG') else '페북/시스템 사용자'}")
    r = requests.get(url, params={"fields": fields, "access_token": tok}, timeout=60)
    d = r.json()
    if r.status_code == 200 and "username" in d:
        print(f"[{name}] 정상: @{d['username']}")
    else:
        ok = False
        print(f"[{name}] 실패 {r.status_code}: {d.get('error', {}).get('message', d)}")
sys.exit(0 if ok else 1)
