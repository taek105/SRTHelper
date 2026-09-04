import hmac
import secrets
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from core.event_logging import log_error, log_event
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
        _log_connect_failure(
            "CONFIGURATION_ERROR",
            "카카오 로그인 설정을 확인할 수 없습니다.",
        )
        log_error("카카오 로그인 URL 생성에 실패했습니다.", exc_info=True)
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
        _log_connect_failure(
            "CONFIGURATION_ERROR",
            "카카오 로그인 설정을 확인할 수 없습니다.",
        )
        log_error("카카오 인증 URL 생성에 실패했습니다.", exc_info=True)
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
    if (
        not state
        or not expected_state
        or not hmac.compare_digest(state, expected_state)
    ):
        _log_connect_failure(
            "INVALID_OAUTH_STATE",
            "유효하지 않은 카카오 로그인 요청입니다.",
        )
        raise HTTPException(status_code=400, detail="잘못된 카카오 로그인 요청입니다.")
    if error:
        _log_connect_failure(
            "OAUTH_CANCELLED",
            "카카오 로그인이 취소되었습니다.",
        )
        raise HTTPException(
            status_code=400,
            detail=f"카카오 로그인이 취소되었습니다: {error}",
        )
    if not code:
        _log_connect_failure(
            "OAUTH_CODE_MISSING",
            "카카오 인가 코드가 없습니다.",
        )
        raise HTTPException(status_code=400, detail="카카오 인가 코드가 없습니다.")

    try:
        exchange_authorization_code(code)
    except KakaoError as exc:
        _log_connect_failure(
            "API_ERROR",
            "카카오 계정 연결에 실패했습니다.",
        )
        log_error("카카오 OAuth 처리에 실패했습니다.", exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        _log_connect_failure(
            "INTERNAL_ERROR",
            "카카오 계정 연결 중 서버 오류가 발생했습니다.",
        )
        raise

    log_event("KAKAO_CONNECTED", result="CONNECTED")
    response = RedirectResponse("/?kakao=connected", status_code=303)
    response.delete_cookie(OAUTH_STATE_COOKIE)
    return response


@router.get("/status")
def kakao_status() -> dict[str, bool]:
    return {"connected": is_kakao_connected()}


@router.post("/test-message")
def kakao_test_message() -> dict[str, bool]:
    if not is_kakao_connected():
        log_event(
            "KAKAO_MESSAGE_FAILED",
            message_type="TEST",
            failure_code="NOT_CONNECTED",
            failure_reason="카카오 로그인이 필요합니다.",
        )
        raise HTTPException(status_code=401, detail="카카오 로그인이 필요합니다.")
    if not send_kakao_message(
        "🚄 KTX Helper 카카오톡 알림 테스트입니다.",
        message_type="TEST",
    ):
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
        log_event(
            "KAKAO_DISCONNECT_FAILED",
            failure_code="TOKEN_STORAGE_ERROR",
            failure_reason="저장된 카카오 로그인 정보를 삭제하지 못했습니다.",
        )
        log_error("카카오 연결 해제에 실패했습니다.", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    log_event("KAKAO_DISCONNECTED", result="DISCONNECTED")
    return {"connected": False}


def _log_connect_failure(failure_code: str, failure_reason: str) -> None:
    log_event(
        "KAKAO_CONNECT_FAILED",
        failure_code=failure_code,
        failure_reason=failure_reason,
    )
