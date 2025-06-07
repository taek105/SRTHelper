from fastapi import APIRouter, Form, Query
from api.srt.controllers.srt_controller import run_macro_logic, run_get_schedule

router = APIRouter()


@router.post("/run", response_model=bool)
def post_run(
    login_id: str              = Form(...),
    login_psw: str             = Form(...),
    from_station: str          = Form(...),
    to_station: str            = Form(...),
    date: str                  = Form(...),
    time: str                  = Form(...),
    reserve: bool              = Form(False),
    seats: list[int]           = Form([])
) -> bool:
    return run_macro_logic(
        login_id=login_id,
        login_psw=login_psw,
        dpt_stn=from_station,
        arr_stn=to_station,
        dpt_dt=date,
        dpt_tm=time,
        target=seats,
        want_reserve=reserve,
    )
    


@router.get("/schedule", response_model=None)
def get_schedule(
    date: str      = Query(..., description="출발일자 YYYYMMDD"),
    time: str      = Query(..., description="출발시간 HHMM or HH:MM"),
    from_station: str = Query(..., description="출발역 이름"),
    to_station: str   = Query(..., description="도착역 이름"),
):

    return run_get_schedule(from_station, to_station, date, time)