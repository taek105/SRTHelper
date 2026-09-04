import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request

from api.kakao import router as kakao_router


def make_request(
    path: str,
    *,
    host: str = "localhost:8000",
    cookie: str | None = None,
) -> Request:
    headers = [(b"host", host.encode("utf-8"))]
    if cookie:
        headers.append((b"cookie", cookie.encode("utf-8")))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": headers,
            "query_string": b"",
            "scheme": "http",
            "server": tuple(host.split(":")),
            "client": ("127.0.0.1", 12345),
        }
    )


class KakaoRouterTest(unittest.TestCase):
    @patch.object(
        kakao_router,
        "get_redirect_uri",
        return_value="http://localhost:8000/auth/kakao/callback",
    )
    @patch.object(kakao_router, "build_authorization_url")
    @patch.object(kakao_router.secrets, "token_urlsafe", return_value="csrf-state")
    def test_login_redirects_to_kakao_and_sets_state_cookie(
        self,
        _token_urlsafe,
        build_authorization_url,
        _get_redirect_uri,
    ):
        build_authorization_url.return_value = "https://kauth.kakao.com/oauth/authorize"
        request = make_request("/auth/kakao/login")

        response = kakao_router.kakao_login(request)

        self.assertEqual(302, response.status_code)
        self.assertEqual(
            "https://kauth.kakao.com/oauth/authorize",
            response.headers["location"],
        )
        self.assertIn("kakao_oauth_state=csrf-state", response.headers["set-cookie"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])

    @patch.object(
        kakao_router,
        "get_redirect_uri",
        return_value="http://localhost:8000/auth/kakao/callback",
    )
    def test_login_canonicalizes_127_host_before_setting_cookie(
        self,
        _get_redirect_uri,
    ):
        request = make_request(
            "/auth/kakao/login",
            host="127.0.0.1:8000",
        )

        response = kakao_router.kakao_login(request)

        self.assertEqual(302, response.status_code)
        self.assertEqual(
            "http://localhost:8000/auth/kakao/login",
            response.headers["location"],
        )
        self.assertNotIn("set-cookie", response.headers)

    @patch.object(kakao_router, "log_event")
    @patch.object(kakao_router, "exchange_authorization_code")
    def test_callback_exchanges_code_after_state_validation(
        self,
        exchange_code,
        log_event,
    ):
        request = make_request(
            "/auth/kakao/callback",
            cookie="kakao_oauth_state=csrf-state",
        )

        response = kakao_router.kakao_callback(
            request,
            code="authorization-code",
            state="csrf-state",
            error=None,
        )

        self.assertEqual(303, response.status_code)
        self.assertEqual("/?kakao=connected", response.headers["location"])
        exchange_code.assert_called_once_with("authorization-code")
        log_event.assert_called_once_with("KAKAO_CONNECTED", result="CONNECTED")

    @patch.object(kakao_router, "log_event")
    def test_callback_rejects_mismatched_state(self, log_event):
        request = make_request(
            "/auth/kakao/callback",
            cookie="kakao_oauth_state=expected-state",
        )

        with self.assertRaises(HTTPException) as raised:
            kakao_router.kakao_callback(
                request,
                code="authorization-code",
                state="different-state",
                error=None,
            )

        self.assertEqual(400, raised.exception.status_code)
        log_event.assert_called_once_with(
            "KAKAO_CONNECT_FAILED",
            failure_code="INVALID_OAUTH_STATE",
            failure_reason="유효하지 않은 카카오 로그인 요청입니다.",
        )

    @patch.object(kakao_router, "send_kakao_message", return_value=True)
    @patch.object(kakao_router, "is_kakao_connected", return_value=True)
    def test_sends_test_message_when_connected(self, _connected, send_message):
        result = kakao_router.kakao_test_message()

        self.assertEqual({"sent": True}, result)
        send_message.assert_called_once_with(
            "🚄 KTX Helper 카카오톡 알림 테스트입니다.",
            message_type="TEST",
        )

    @patch.object(kakao_router, "log_event")
    @patch.object(kakao_router, "clear_token_data")
    def test_logs_disconnect(self, clear_token_data, log_event):
        result = kakao_router.kakao_disconnect()

        self.assertEqual({"connected": False}, result)
        clear_token_data.assert_called_once_with()
        log_event.assert_called_once_with(
            "KAKAO_DISCONNECTED",
            result="DISCONNECTED",
        )


if __name__ == "__main__":
    unittest.main()
