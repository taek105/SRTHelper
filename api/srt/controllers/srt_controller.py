from services.srt import SRT, get_schedule

def run_macro_logic(
    login_id: str, 
    login_psw: str, 
    dpt_stn: str,
    arr_stn: str,
    dpt_dt: str,
    dpt_tm: str,
    target: list[int],
    want_reserve: bool) -> dict:

    srt = SRT(dpt_stn, arr_stn, dpt_dt, dpt_tm, target, want_reserve)
    return srt.run(login_id, login_psw)
    
    
def run_get_schedule(dpt_stn, arr_stn, date, tm):
    
    return get_schedule(dpt_stn, arr_stn, date, tm)