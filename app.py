from time import perf_counter
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

from api.kakao.router import router as kakao_router
from api.srt.router import api_router
from core.event_logging import (
    configure_logging,
    log_error,
    log_event,
    reset_request_id,
    set_request_id,
)
from service.ktx import KTX_STATIONS

configure_logging()

app = FastAPI()
app.include_router(api_router)
app.include_router(kakao_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

LOGGED_REQUEST_PREFIXES = ("/run", "/schedule", "/auth/kakao")


@app.middleware("http")
async def add_request_logging(request: Request, call_next):
    request_id = uuid4().hex
    context_token = set_request_id(request_id)
    started_at = perf_counter()
    should_log = request.url.path.startswith(LOGGED_REQUEST_PREFIXES)
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((perf_counter() - started_at) * 1000)
        if should_log:
            log_event(
                "HTTP_REQUEST_FAILED",
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
            )
        log_error(
            "처리되지 않은 HTTP 요청 오류가 발생했습니다.",
            exc_info=True,
            method=request.method,
            path=request.url.path,
        )
        raise
    else:
        response.headers["X-Request-ID"] = request_id
        if should_log:
            log_event(
                "HTTP_REQUEST_FINISHED",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round((perf_counter() - started_at) * 1000),
            )
        return response
    finally:
        reset_request_id(context_token)


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

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        access_log=False,
    )
