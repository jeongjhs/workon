# CJ World 좌석 예약 자동화

CJ World 외부망 인증을 통한 자율좌석 자동 예약 스크립트입니다.

## 주요 기능

- CJ World 외부망 로그인 (이메일 인증 방식)
- Gmail을 통한 인증코드 자동 수신
- 자율좌석 자동 예약 (14일 후 좌석)
- 예약 가능 요일 필터링 (수/목/금요일만 예약)
- 공휴일 및 특정 금요일(2째주, 4째주) 자동 제외
- 우선순위 기반 좌석 선택 (첫 번째 좌석 실패 시 다음 좌석 시도)

## 요구사항

- Python 3.11 이상
- Gmail 계정 (앱 비밀번호 필요)
- CJ World 계정

## 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd workon
```

### 2. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

## 환경 변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 정보를 입력하세요:

```env
CJ_USERNAME=your_cj_username
CJ_PASSWORD=your_cj_password
GMAIL_ADDRESS=your_gmail@gmail.com
GMAIL_APP_PASSWORD=your_16_digit_app_password
```

### Gmail 앱 비밀번호 생성 방법

1. [Google 계정 관리](https://myaccount.google.com/)에 접속
2. **보안** > **2단계 인증** (활성화되어 있지 않다면 먼저 활성화)
3. **보안** > **앱 비밀번호** 클릭
4. 앱 선택: "메일", 기기 선택: "기타"
5. 생성된 16자리 비밀번호를 `.env` 파일의 `GMAIL_APP_PASSWORD`에 입력

## 로컬 실행

환경 변수 설정이 완료되면 다음 명령어로 스크립트를 실행할 수 있습니다:

```bash
python workon_new.py
```

### 실행 프로세스

1. CJ World 세션 초기화
2. 사용자 인증 정보 전송
3. 이메일 인증코드 요청
4. Gmail에서 인증코드 자동 수신 (최대 60초 대기)
5. 인증코드 제출 및 로그인 완료
6. 14일 후 좌석 예약 시도

## GitHub Actions 스케줄 등록

이 프로젝트는 GitHub Actions를 사용하여 자동으로 좌석을 예약할 수 있습니다.

### 1. GitHub Secrets 설정

GitHub 저장소에서 다음 Secrets를 등록해야 합니다:

1. GitHub 저장소 페이지로 이동
2. **Settings** 탭 클릭
3. 왼쪽 메뉴에서 **Secrets and variables** > **Actions** 클릭
4. **New repository secret** 버튼 클릭
5. 다음 4개의 Secret을 각각 등록:

| Name | Value |
|------|-------|
| `CJ_USERNAME` | CJ World 사용자 ID |
| `CJ_PASSWORD` | CJ World 비밀번호 |
| `GMAIL_ADDRESS` | Gmail 주소 |
| `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 (16자리) |

### 2. 스케줄 확인 및 수정

현재 스케줄은 `.github/workflows/daily-reservation.yml` 파일에 정의되어 있습니다:

```yaml
schedule:
  # 수/목/금 00:01 KST (전날 15:01 UTC)
  - cron: '1 15 * * 3,4,5'
```

#### 스케줄 변경 방법

cron 표현식을 수정하여 실행 시간을 변경할 수 있습니다:

```
분 시 일 월 요일
```

예시:
- `1 15 * * 2,3,4` - 화/수/목 00:01 KST (월/화/수 15:01 UTC)
- `30 14 * * 1,2,3,4,5` - 월~금 23:30 KST (14:30 UTC)

**참고**: GitHub Actions는 UTC 기준으로 동작하므로 KST(UTC+9)에서 9시간을 빼야 합니다.

### 3. 수동 실행

GitHub Actions 워크플로우를 수동으로 실행할 수도 있습니다:

1. GitHub 저장소의 **Actions** 탭으로 이동
2. 왼쪽 메뉴에서 **Daily Seat Reservation** 클릭
3. 오른쪽의 **Run workflow** 버튼 클릭
4. **Run workflow** 확인

### 4. 실행 로그 확인

1. GitHub 저장소의 **Actions** 탭으로 이동
2. 최근 워크플로우 실행 내역 클릭
3. **reserve-seat** 작업 클릭하여 상세 로그 확인

## 예약 규칙

스크립트는 다음 규칙에 따라 좌석을 예약합니다:

### 예약 대상일

- 오늘로부터 **14일 후** 날짜
- **수요일, 목요일, 금요일**만 예약
- **공휴일 제외**
- **매월 2째주, 4째주 금요일 제외**

### 좌석 우선순위

다음 순서대로 좌석 예약을 시도합니다 (첫 번째 좌석 실패 시 다음 좌석 시도):

1. `004-001`
2. `004-005`
3. `004-002`
4. `004-006`
5. `004-003`
6. `004-007`
7. `004-004`
8. `004-008`

### 예약 시간

- 기본 시간: 08:00 ~ 17:00
- `workon_new.py`의 `reserve_seat()` 함수 파라미터로 변경 가능

## 문제 해결

### 인증코드를 받지 못하는 경우

1. Gmail 앱 비밀번호가 올바른지 확인
2. Gmail 보안 설정에서 "보안 수준이 낮은 앱" 허용 확인
3. 스팸 폴더 확인

### 좌석 예약이 실패하는 경우

1. 네트워크 연결 상태 확인
2. CJ World 계정 정보가 올바른지 확인
3. 예약하려는 날짜가 예약 가능한 날짜인지 확인 (수/목/금, 공휴일 제외)
4. 모든 좌석이 이미 예약되었을 가능성 확인

### GitHub Actions가 실행되지 않는 경우

1. GitHub Secrets가 모두 올바르게 등록되었는지 확인
2. 워크플로우 파일의 cron 표현식 확인
3. 저장소의 Actions가 활성화되어 있는지 확인

## 프로젝트 구조

```
workon/
├── .github/
│   └── workflows/
│       └── daily-reservation.yml    # GitHub Actions 워크플로우
├── workon_new.py                     # 메인 스크립트
├── requirements.txt                  # Python 의존성 패키지
├── .env                              # 환경 변수 (직접 생성 필요)
└── README.md                         # 이 문서
```

## 라이선스

이 프로젝트는 개인용으로 제작되었습니다.
