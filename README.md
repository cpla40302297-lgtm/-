# 🎵 N Band Writer
### 네이버 밴드 자동 게시물 작성 프로그램

Band Open API를 활용한 데스크톱 자동화 도구  
(원본 프로그램 ckm-marketing/NBandWriter 과 유사한 기능)

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 📤 **즉시 게시** | 선택한 밴드에 즉시 게시물 업로드 |
| 📅 **예약 게시** | 원하는 날짜/시간에 자동 게시 (1회/매일/매주 반복) |
| 📷 **이미지 첨부** | 이미지 파일 첨부 게시 |
| 📳 **푸시 알림** | 멤버에게 푸시 알림 전송 옵션 |
| 📋 **템플릿 관리** | 자주 쓰는 게시문 템플릿 저장/불러오기 |
| ⚙️ **설정 저장** | API 키, 토큰 로컬 저장 |

---

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 실행
```bash
python main.py
```

---

## 🔑 Band API 키 발급 방법

1. [BAND Developers](https://developers.band.us) 접속
2. **Register Service** → 앱 등록
3. Redirect URI에 `http://localhost:9988/callback` 입력
4. 발급된 **Client ID**, **Client Secret** 복사

---

## 📖 사용법

### Step 1 - API 키 설정
1. 우측 사이드바 **⚙️ 설정** 클릭
2. Client ID, Client Secret 입력 후 **설정 저장**

### Step 2 - 밴드 로그인
1. **설정** 페이지에서 **🔑 브라우저로 로그인** 클릭
2. 브라우저에서 네이버 밴드 계정으로 인증
3. 자동으로 토큰 저장됨

### Step 3 - 게시물 작성
1. **✏️ 게시물 작성** 페이지로 이동
2. 밴드 선택 (🔄 새로고침 후 선택)
3. 내용 작성
4. 이미지 첨부 (선택)
5. **📤 게시물 올리기** 클릭

### 예약 게시
- 게시물 작성 화면에서 **⏰ 예약 게시 사용** 체크
- 날짜/시간 설정 후 올리기
- **📅 예약 게시** 탭에서 예약 목록 확인/삭제

---

## 📁 파일 구조

```
N-Band-Writer/
├── main.py              # 실행 진입점
├── requirements.txt     # 의존성
├── config.json          # 설정 파일 (자동 생성)
├── schedules.json       # 예약 목록 (자동 생성)
├── src/
│   ├── app.py          # 메인 GUI
│   ├── band_api.py     # Band Open API 클라이언트
│   ├── config_manager.py # 설정 관리
│   └── scheduler.py    # 예약 스케줄러
└── assets/             # 아이콘 등 리소스
```

---

## ⚠️ 주의사항

- Band Open API는 **공식 발급 토큰**이 필요합니다
- 자동화 남용 시 계정이 제한될 수 있으니 적절히 사용하세요
- 토큰은 `config.json`에 로컬 저장됩니다 (외부 공유 금지)

---

## 🛠️ 기술 스택

- **Python 3.8+**
- **tkinter** - GUI
- **requests** - HTTP 클라이언트
- **Band Open API v2.2**
