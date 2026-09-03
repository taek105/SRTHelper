from service.kakao import notify_booking_success
from service.ktx import KTX, get_schedule


def run_macro_logic(
    login_id: str, 
    login_psw: str, 
    dpt_stn: str,
    arr_stn: str,
    dpt_dt: str,
    dpt_tm: str,
    target: list[int],
    want_reserve: bool,
) -> bool:

    ktx = KTX(
        dpt_stn,
        arr_stn,
        dpt_dt,
        dpt_tm,
        target,
        want_reserve,
    )
    is_booked = ktx.run(login_id, login_psw)

    if is_booked:
        notify_booking_success(
            from_station=dpt_stn,
            to_station=arr_stn,
            departure_date=dpt_dt,
            departure_time=dpt_tm,
        )

    return is_booked
    
    
def run_get_schedule(dpt_stn, arr_stn, date, tm):
    
    return get_schedule(dpt_stn, arr_stn, date, tm)
