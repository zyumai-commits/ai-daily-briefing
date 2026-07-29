# GitHub만으로 매일 AI 카드뉴스 → 내 카카오톡

GCP·리눅스 VM·서버 접속이 필요 없습니다. GitHub Actions가 매일 한국 시간 오전 10시에 실행되고, GitHub Pages에 카드뉴스를 올린 뒤 카카오 나에게 보내기 API를 호출합니다.

## 파일 구성 (저장소에 이 구조 그대로 올리기)

- `.github/workflows/daily-briefing.yml` ← 지금은 `daily-briefing.yml`로 있음. 저장소에는 반드시 `.github/workflows/` 폴더 안에 넣어야 합니다.
- `github_generate.py` — RSS 뉴스 수집 → OpenAI 요약 → 카드 이미지 + index.html 생성
- `github_send_kakao.py` — 카카오 나에게 보내기 API 호출
- `kakao_oauth_helper.py` — 카카오 refresh token 발급 도우미 (내 PC에서 1회만 실행)

## 1. GitHub 저장소 만들기

1. GitHub에서 새 Public 저장소를 만듭니다. 카드뉴스 페이지와 대표 이미지는 카카오가 읽어야 하므로 공개됩니다.
2. 이 폴더의 파일을 저장소에 올립니다. `daily-briefing.yml`은 `.github/workflows/daily-briefing.yml` 경로에 위치해야 합니다.
3. 저장소 Settings → Pages → Build and deployment → Source에서 GitHub Actions를 선택합니다.

## 2. 카카오 refresh token 만들기 — 내 PC에서 한 번만

Kakao Developers의 앱 → 플랫폼 키 → REST API 키에서 리다이렉트 URI에 아래를 추가하고 저장합니다.

http://localhost:8765/callback

그 다음 내 PC에서 이 폴더를 열어 실행합니다.

    pip install requests
    python kakao_oauth_helper.py

브라우저에서 카카오 로그인과 메시지 전송 동의를 끝내면 터미널에 refresh token이 나옵니다. 이 값은 절대 채팅·GitHub 코드·스크린샷에 넣지 않습니다.

## 3. GitHub Secrets 등록

저장소 Settings → Secrets and variables → Actions → New repository secret에서 다음 네 개를 추가합니다.

- OPENAI_API_KEY: OpenAI API 키
- KAKAO_REST_API_KEY: 카카오 REST API 키
- KAKAO_CLIENT_SECRET: 카카오 로그인용 Client Secret
- KAKAO_REFRESH_TOKEN: 위에서 발급한 refresh token

선택적으로 Variables에 OPENAI_MODEL(기본값 gpt-4.1-mini)과 NEWS_FEEDS를 설정할 수 있습니다.

## 4. 첫 실행과 카카오 링크 설정

1. Actions → Daily AI card news → Run workflow를 눌러 수동 실행합니다.
2. 성공 후 deploy 작업에서 GitHub Pages 주소를 확인합니다. 보통 https://계정명.github.io/저장소명/ 형태입니다.
3. Kakao Developers의 앱 → 제품 링크 관리 → 웹 도메인에 https://계정명.github.io 를 등록합니다.
4. workflow를 한 번 더 수동 실행합니다. 이제 내 카카오톡에 카드가 옵니다.

정기 실행은 .github/workflows/daily-briefing.yml의 0 1 * * *(UTC), 즉 한국 시간 오전 10시입니다. GitHub 예약 실행은 몇 분 지연될 수 있습니다.

## 보안과 범위

- 카카오 로그인 Client Secret이 스크린샷에 드러났다면 코드 재발급 후 새 값만 사용하세요.
- GitHub Pages는 공개이므로 개인 정보·비공개 자료를 카드에 넣지 마세요.
- 공식 Kakao API 제약상 자동 발송 대상은 나와의 채팅입니다. 단체방에는 결과를 확인한 뒤 직접 공유합니다.
