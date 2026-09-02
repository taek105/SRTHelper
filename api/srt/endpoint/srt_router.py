from fastapi import APIRouter, Form, HTTPException, Query

from api.srt.controller.srt_controller import run_get_schedule, run_macro_logic
from service.exceptions import (
    BrowserWindowClosedError,
    InvalidPhoneNumberError,
    KorailAccessBlockedError,
)

router = APIRouter()


@router.post("/run", response_model=bool)
def post_run(
    login_id: str = Form(...),
    login_psw: str = Form(...),
    from_station: str = Form(...),
    to_station: str = Form(...),
    date: str = Form(...),
    time: str = Form(...),
    reserve: bool = Form(False),
    reservation_phone: str | None = Form(None),
    seats: list[int] = Form(default_factory=list),  # noqa: B008
) -> bool:
    try:
        return run_macro_logic(
            login_id=login_id,
            login_psw=login_psw,
            dpt_stn=from_station,
            arr_stn=to_station,
            dpt_dt=date,
            dpt_tm=time,
            target=seats,
            want_reserve=reserve,
            reservation_phone=reservation_phone,
        )
    except BrowserWindowClosedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KorailAccessBlockedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except InvalidPhoneNumberError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@router.get("/schedule", response_model=None)
def get_schedule(
    date: str = Query(..., description="출발일자 YYYYMMDD"),
    time: str = Query(..., description="출발시간 HHMM or HH:MM"),
    from_station: str = Query(..., description="출발역 이름"),
    to_station: str = Query(..., description="도착역 이름"),
):
    try:
        return run_get_schedule(from_station, to_station, date, time)
    except KorailAccessBlockedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
