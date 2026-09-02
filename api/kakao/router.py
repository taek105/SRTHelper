import hmac
import secrets
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from service.kakao import (
    KakaoError,
    build_authorization_url,
    clear_token_data,
    exchange_authorization_code,
    get_redirect_uri,
    is_kakao_connected,
    send_kakao_message,
)


router = APIRouter(prefix="/auth/kakao", tags=["kakao"])
OAUTH_STATE_COOKIE = "kakao_oauth_state"


@router.get("/login")
def kakao_login(request: Request) -> RedirectResponse:
    try:
        redirect_uri = get_redirect_uri()
    except KakaoError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    callback_url = urlparse(redirect_uri)
    callback_origin = f"{callback_url.scheme}://{callback_url.netloc}"
    request_origin = f"{request.url.scheme}://{request.url.netloc}"
    if request_origin != callback_origin:
        return RedirectResponse(
            f"{callback_origin}/auth/kakao/login",
            status_code=302,
        )

    state = secrets.token_urlsafe(32)
    try:
        authorization_url = build_authorization_url(state)
    except KakaoError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    response = RedirectResponse(authorization_url, status_code=302)
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/callback")
def kakao_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    expected_state = request.cookies.get(OAUTH_STATE_COOKIE, "")
    if not state or not expected_state or not hmac.compare_digest(state, expected_state):
        raise HTTPException(status_code=400, detail="잘못된 카카오 로그인 요청입니다.")
    if error:
        raise HTTPException(status_code=400, detail=f"카카오 로그인이 취소되었습니다: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="카카오 인가 코드가 없습니다.")

    try:
        exchange_authorization_code(code)
    except KakaoError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    response = RedirectResponse("/?kakao=connected", status_code=303)
    response.delete_cookie(OAUTH_STATE_COOKIE)
    return response


@router.get("/status")
def kakao_status() -> dict[str, bool]:
    return {"connected": is_kakao_connected()}


@router.post("/test-message")
def kakao_test_message() -> dict[str, bool]:
    if not is_kakao_connected():
        raise HTTPException(status_code=401, detail="카카오 로그인이 필요합니다.")
    if not send_kakao_message("🚄 KTX Helper 카카오톡 알림 테스트입니다."):
        raise HTTPException(
            status_code=502,
            detail="카카오톡 테스트 메시지를 보내지 못했습니다. 서버 로그를 확인해 주세요.",
        )
    return {"sent": True}


@router.post("/disconnect")
def kakao_disconnect() -> dict[str, bool]:
    try:
        clear_token_data()
    except KakaoError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"connected": False}
