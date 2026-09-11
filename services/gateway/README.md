# services/gateway

`/dev`(브라우저 음성인식) → `server/apps/hub`(마스킹) → `apps/dashboard`(WebSocket)
로 이어지는 실시간 자막 배선. A-3(브라우저 실시간 전달) 자리를 채운다.

담당 경계는 `_project/decisions/012`상 정성윤이다 — 2026-09-10 사용자 지시로
조서희가 만들었다(`decisions/023`에 따라 협의 없이 진행, 경계를 넘은 사실만
기록으로 남긴다).

⚠ **실제 전화망(Twilio 등) 연동은 없다** (2026-09-11, 사용자 지시로 제거).
A-1/A-2 본체(실제 전화 → STT)는 여전히 팀의 미완료 항목이다 — 전화 사업자를
고르고 Google Cloud STT 자격증명을 서버 쪽에서 호출하는 코드가 다시 필요해지면
그때 새로 만든다. 지금 이 디렉터리는 "게이트웨이 → hub → 대시보드" 배선이
실제로 도는지 확인하는 용도로만 쓴다.

## 로컬 실행

```bash
cd services/gateway
npm install
```

`.env`에 채울 것:

| 키 | 값 |
|---|---|
| `GATEWAY_PORT` | 기본 8080 |
| `HUB_API_URL` | `server/apps/hub`가 떠 있는 주소. 개인 테스트는 배포된 `https://server.solidbob.cloud` 를 바로 써도 된다 |

```bash
npm start
```

## 개발용 테스트 콜 — 전화 사업자·STT 자격증명 없이

`GET /dev` 페이지가 개발자 본인 폰(또는 컴퓨터) 브라우저만으로 "통화"를 흉내 낸다.
서버로 오디오를 보내지 않는다 — **브라우저 내장 Web Speech API로 그 자리에서 바로
텍스트로 바꿔** WebSocket으로 보낸다. 그래서 GCP 프로젝트·서비스 계정 키가 전혀
필요 없다. STT 품질 자체를 보려면(정식 파이프라인 검증) 나중에 팀 쪽 실제 STT
경로로 다시 확인해야 한다. Chrome(폰·데스크톱 둘 다) 기준으로 테스트했다 — Safari는
Web Speech API 지원이 불안정하다.

**필요한 건 ngrok(무료)뿐이다** — 전화망 사업자가 아니라 그냥 HTTPS 터널 서비스라
전화번호·본인인증 없이 이메일만으로 가입된다. 브라우저가 마이크 권한을 HTTPS(또는
localhost)에서만 열어주기 때문에, 폰에서 접속하려면 이 터널이 필요하다.

```bash
npm start            # 게이트웨이 8080에서 기동
ngrok http 8080       # 별도 터미널. https://<발급된 주소>.ngrok-free.dev 를 확인
```

1. 폰 브라우저(Chrome)로 `https://<ngrok 주소>/dev` 접속
2. "통화 시작" 버튼 → 마이크 권한 허용
3. 말하면 브라우저가 즉시 텍스트로 바꿔 `/dev/media` WebSocket으로 보낸다 —
   서버 쪽 hub·대시보드 배선은 실제 전화 경로가 생겨도 그대로 재사용된다
4. 대시보드(`apps/dashboard` 로컬 `npm run dev` 이거나, 개인 Vercel 배포)를
   `?gateway=wss://<ngrok 주소>/dashboard` 쿼리로 한 번 열어 라이브 모드로 전환한다
   (`lib/ws/types.ts` 참고 — Vercel 환경변수 없이도 되는 런타임 오버라이드)
5. 콘솔 로그에 `[gateway] 통화 시작 ...`이 뜨고, 대시보드 자막 패널에 발화가
   실시간으로 올라오는지 확인한다
6. "통화 종료" 버튼으로 마친다

## 알려진 제약

- 화자는 전부 `customer`로 표시한다.
- `POST /hub/transcripts` 호출이 실패하면(hub 서버가 안 떠 있을 때 등) 그
  구간은 조용히 버려진다 — 마스킹을 거치지 않은 원문을 대시보드로 보내지
  않기 위해서다(C-5 절대 원칙). 로그에는 남는다.
- 통화 ID에 `test-` 접두어를 기본으로 붙인다(`HUB_CALL_ID_PREFIX`) — hub
  DB에 실제 데이터처럼 영구히 남기지 않으려는 임시 관례다. 실제 서비스로
  올리면 이 접두어를 뗀다.
