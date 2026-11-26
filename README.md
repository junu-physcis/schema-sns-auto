# SCHEMA SNS 자동 게시

- `queue.yaml` : 게시 예약표 (무엇을 · 언제(KST) · 어디에). `hold: true` 는 안 올라감.
- `media/` : 게시 이미지 (공개 주소로 Threads · Instagram 이 가져감)
- `state.json` : 올라간 기록 (자동 갱신)
- `.github/workflows/post.yml` : 10분마다 예약표를 보고 시간이 된 글을 올림. Actions 탭에서 수동 실행 시 id 하나만 테스트 가능.
- `.github/workflows/refresh.yml` : 매주 월요일 토큰 60일 연장
- 금고(Secrets): THREADS_TOKEN · THREADS_APP_SECRET · IG_TOKEN · GH_PAT

블로그(네이버)는 API가 없어 Claude가 크롬에서 예약발행을 건다.
