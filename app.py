from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from api.srt.router import api_router

app = FastAPI()
app.include_router(api_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

STATIONS = ["수서", "동탄", "평택지제", "천안아산", "오송", "대전",
            "김천구미", "동대구", "신경주", "울산(통도사)", "부산",
            "공주", "익산", "정읍", "광주송정", "나주", "목포"]

@app.get("/", response_class=HTMLResponse)
def get_form(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "station_list": STATIONS
    })

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run("app:app", host="127.0.0.1", port=8000)