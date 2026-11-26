"""게시하지 않고 인스타 컨테이너만 만들어 alt_text 지원 여부를 확인한다 (24시간 뒤 자동 소멸)."""
import os, requests
tok = os.environ["IG_TOKEN"]
host = "https://graph.instagram.com/v22.0/me" if tok.startswith("IG") else "https://graph.facebook.com/v22.0/17841445606722579"
img = "https://raw.githubusercontent.com/junu-physcis/schema-sns-auto/main/media/ig-1p-01/01.jpg"
for name, extra in [("alt_text", {"alt_text": "테스트 대체 텍스트"}), ("location_id(잘못된 값)", {"location_id": "1"})]:
    r = requests.post(f"{host}/media", params={"image_url": img, "caption": "test", "access_token": tok, **extra}, timeout=60)
    d = r.json()
    print(name, r.status_code, d.get("id") and "컨테이너 생성됨(게시 안 함)" or d.get("error", {}).get("message"))
