# KTX helper
<p>
    <!-- <img width="128" height="128" alt="image" src="https://github.com/user-attachments/assets/2f700449-a605-43fa-a2b2-bd3d7a2eb2e6"> -->
    <img width="128" height="128" alt="image" src="https://github.com/user-attachments/assets/8e9eba99-3ac3-4dff-9edb-296c5adf1db1" />

</p>

<p>
    <img alt="Static Badge" src="https://img.shields.io/badge/python-3.11-blue?style=flat&logo=python&logoColor=white">
    <img alt="Static Badge" src="https://img.shields.io/badge/google chrome-latest-white?style=flat&logo=googlechrome&logoColor=white">
</p>

![2025-06-07 23;48;31](https://github.com/user-attachments/assets/510d5d27-50a4-4cf3-803b-e15a774c2cc7)

매진된 KTX 표의 예매를 도와주는 파이썬 프로그램입니다.
mac 환경에서 실행 가능합니다.

  
## requirements
- ***Python 3.11.****
- 최신 버전의 크롬 브라우저

```
selenium==4.48.0
webdriver-manager==4.1.2
fastapi==0.141.1
uvicorn==0.52.4
jinja2==3.1.6
python-multipart==0.0.32
undetected-chromedriver==3.5.5
python-dotenv==1.2.3
```

## 사용법
- 백오피스 탭을 활성화하지 않으면 사이렌이 울리지 않습니다. (카톡 알림은 옵니다)
- 도우미가 동작하는 탭을 조작하면 제대로 동작하지 않습니다. 
    - 포커스를 두지 않는 것을 추천
    - 최소화 하는 것을 추천
 

```py
0. 패키지의 루트 디렉토리로 이동
1. python -m venv .venv
2. (mac) source .venv/bin/activate or (window) ./.venv/scripts/activate.ps1
3. pip install -r requirements.txt
4. python app.py
5. localhost:8000 접속
```


## 기타  
과도한 사용은 지양해 주십시오.
