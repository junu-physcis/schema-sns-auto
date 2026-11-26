# SCHEMA SNS 자동 게시

- `queue.yaml` : 게시 예약표 (무엇을 · 언제(KST) · 어디에). `hold: true` 는 안 올라감.
- `media/` : 게시 이미지 (공개 주소로 Threads · Instagram 이 가져감)
- `state.json` : 올라간 기록 (자동 갱신)
- `.github/workflows/post.yml` : 10분마다 예약표를 보고 시간이 된 글을 올림. Actions 탭에서 수동 실행 시 id 하나만 테스트 가능.
- `.github/workflows/refresh.yml` : 매주 월요일 토큰 60일 연장
- 금고(Secrets): THREADS_TOKEN · THREADS_APP_SECRET · IG_TOKEN · GH_PAT

블로그(네이버)는 API가 없어 Claude가 크롬에서 예약발행을 건다.

## 예약표 한 줄 형식
```yaml
- id: th-07            # 고유 이름 (채널-번호)
  channel: threads     # threads | instagram
  at: 2026-12-14 21:00 # 한국 시간
  hold: true           # true면 안 올라감
  slot: 정보           # 총괄팀 리듬 표시(정보/증거/모집), 게시엔 영향 없음
  topic_tag: 고2물리   # 스레드 주제 태그 1개 (선택)
  text: |              # 본글 또는 인스타 캡션
    ...
  images: [media/...jpg]   # 인스타 캐러셀 최대 10장, 스레드 최대 20장
  video: media/...mp4      # 인스타 릴스일 때 (images 대신)
  cover: media/...jpg      # 릴스 표지 (선택)
  replies:                 # 스레드 답글 타래 (선택, 링크는 여기에)
    - text: ...
      images: [...]
```
