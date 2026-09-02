from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

from api.kakao.router import router as kakao_router
from api.srt.router import api_router
from service.ktx import KTX_STATIONS

app = FastAPI()
app.include_router(api_router)
app.include_router(kakao_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def get_form(request: Request):
    return templates.TemplateResponse(
        name="index.html",
        request=request,
        context={
            "station_list": KTX_STATIONS
        })

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run("app:app", host="127.0.0.1", port=8000)
