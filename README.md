# SRT helper 
<p>
    <img alt="Static Badge" src="https://img.shields.io/badge/python-3.11-blue?style=flat&logo=python&logoColor=white">
    <img alt="Static Badge" src="https://img.shields.io/badge/google chrome-latest-white?style=flat&logo=googlechrome&logoColor=white">
</p>

![2025-06-07 23;48;31](https://github.com/user-attachments/assets/510d5d27-50a4-4cf3-803b-e15a774c2cc7)

매진된 SRT 표의 예매를 도와주는 파이썬 프로그램입니다.  
PC 환경에서만 실행 가능합니다.  

  
## 필요
- ***Python 3.11.****
- 최신 버전의 크롬 브라우저

```
- selenium
- webdriver_manager
- fastapi
- uvicorn[standard]
- jinja2
- python-multipart
- undetected-chromedriver
```

## 사용법
- 백오피스 탭을 활성화하지 않으면 예약 성공 알림이 동작하지 않습니다.
- 맥 버전에서는 날짜, 시간을 선택하는 도중 탭을 조작할 수 없습니다.
- 도우미가 동작하는 탭을 조작하면 제대로 동작하지 않습니다. 
    - 창을 가로로 좁게 두어서 상단 네비게이터를 없애는 것을 추천
    - 포커스를 두지 않는 것을 추천
 

```py
0. 패키지의 루트 디렉토리로 이동
1. python -m venv .venv
2. source .venv/bin/activate or ./.venv/scripts/activate.ps1
3. pip install -r requirements.txt
4. python app.py
5. localhost:8000 접속
```

## 카카오톡 예매 성공 알림

예매에 성공하면 웹 사이렌과 함께 카카오톡 `나에게 보내기` 메시지를 전송합니다.

1. 카카오 Developers 앱에서 카카오 로그인을 활성화합니다.
2. `카카오톡 메시지 전송(talk_message)` 동의항목을 설정합니다.
3. REST API 키의 리다이렉트 URI에 아래 주소를 등록합니다.
   - `http://localhost:8000/auth/kakao/callback`
4. `제품 링크 관리 > 웹 도메인`에 메시지 버튼으로 사용할 도메인을 등록합니다.
   - 기본값: `https://etk.srail.kr`
5. `.env.example`을 `.env`로 복사하고 앱 설정값을 입력합니다.

```dotenv
KAKAO_REST_API_KEY=카카오_앱의_REST_API_키
KAKAO_CLIENT_SECRET=REST_API_키의_클라이언트_시크릿
KAKAO_REDIRECT_URI=http://localhost:8000/auth/kakao/callback
KAKAO_MESSAGE_LINK_URL=https://etk.srail.kr
```

앱 실행 후 `http://localhost:8000`에 접속해 **카카오 로그인** 버튼을 누릅니다.
로그인이 끝나면 액세스 토큰과 리프레시 토큰은 `.kakao_tokens.json`에 저장되며,
액세스 토큰 만료 시 자동으로 갱신됩니다. 토큰 파일과 `.env`는 Git에서 제외됩니다.

화면의 **알림 테스트** 버튼으로 `나에게 보내기` 동작을 바로 확인할 수 있습니다.
카카오 API 호출에 실패하더라도 이미 완료된 예매와 웹 사이렌은 정상 처리되며,
카카오 전송 오류는 서버 로그에서 확인할 수 있습니다.


## 기타  
명절 승차권 예약에는 사용이 불가합니다.   
과도한 사용은 지양해 주십시오.
