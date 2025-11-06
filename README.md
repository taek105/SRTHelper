# SRT helper 
<p>
    <img alt="Static Badge" src="https://img.shields.io/badge/python-3.13-blue?style=flat&logo=python&logoColor=white">
    <img alt="Static Badge" src="https://img.shields.io/badge/google chrome-latest-white?style=flat&logo=googlechrome&logoColor=white">
</p>

![2025-06-07 23;48;31](https://github.com/user-attachments/assets/510d5d27-50a4-4cf3-803b-e15a774c2cc7)

매진된 SRT 표의 예매를 도와주는 파이썬 프로그램입니다.  
PC 환경에서만 실행 가능합니다.  
https://github.com/kminito/srt_reservation 를 참고했습니다.

  
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
- 도우미가 동작하는 탭을 조작하면 제대로 동작하지 않습니다. 
    - 창을 가로로 좁게 두어서 상단 네비게이터를 없애는 것을 추천
    - 포커스를 두지 않는 것 추천
 

```py
0. 패키지의 루트 디렉토리로 이동
1. python -m venv .venv
2. source .venv/bin/activate or ./.venv/scripts/activate.ps1
3. pip install -r requirements.txt
4. python app.py
5. localhost:8000 접속
```


## 기타  
명절 승차권 예약에는 사용이 불가합니다.   
과도한 사용은 지양해 주십시오.
