import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchWindowException,
)

from api.srt.endpoint import srt_router
from service import ktx as ktx_module
from service.exceptions import (
    BrowserWindowClosedError,
    InvalidPhoneNumberError,
    KorailAccessBlockedError,
)


class BrowserWindowStateTest(unittest.TestCase):
    def setUp(self):
        self.ktx = ktx_module.KTX(
            dpt_stn="서울",
            arr_stn="부산",
            dpt_dt="20260814",
            dpt_tm="00",
            target_index=[1],
        )
        self.ktx.driver = MagicMock()

    def prepare_run(self):
        self.ktx.run_driver = MagicMock()
        self.ktx.set_log_info = MagicMock()
        self.ktx.login = MagicMock()
        self.ktx.check_login = MagicMock()
        self.ktx.go_search = MagicMock()
        self.ktx.check_result = MagicMock()

    @patch("builtins.print")
    def test_run_stops_when_browser_window_is_closed(self, print_mock):
        self.prepare_run()
        self.ktx.check_result.side_effect = NoSuchWindowException(
            "target window already closed"
        )

        with self.assertRaisesRegex(
            BrowserWindowClosedError,
            "브라우저 창이 닫혀 매크로를 종료합니다.",
        ) as raised:
            self.ktx.run("login-id", "login-password")

        self.assertIsInstance(raised.exception.__cause__, NoSuchWindowException)
        print_mock.assert_called_once_with(
            "[매크로 종료] 브라우저 창이 닫혀 매크로를 종료합니다."
        )

    @patch("builtins.print")
    def test_run_stops_when_browser_session_is_invalid(self, print_mock):
        self.prepare_run()
        self.ktx.login.side_effect = InvalidSessionIdException(
            "invalid session id"
        )

        with self.assertRaises(BrowserWindowClosedError) as raised:
            self.ktx.run("login-id", "login-password")

        self.assertIsInstance(
            raised.exception.__cause__,
            InvalidSessionIdException,
        )
        self.ktx.check_login.assert_not_called()
        print_mock.assert_called_once_with(
            "[매크로 종료] 브라우저 창이 닫혀 매크로를 종료합니다."
        )


class BrowserWindowApiTest(unittest.TestCase):
    @patch.object(
        srt_router,
        "run_macro_logic",
        side_effect=BrowserWindowClosedError("브라우저 창이 닫혔습니다."),
    )
    def test_post_run_returns_conflict_for_closed_browser(self, _run_macro):
        with self.assertRaises(HTTPException) as raised:
            srt_router.post_run(
                login_id="login-id",
                login_psw="login-password",
                from_station="서울",
                to_station="부산",
                date="20260814",
                time="00",
                reserve=False,
                reservation_phone=None,
                seats=[1],
            )

        self.assertEqual(409, raised.exception.status_code)
        self.assertEqual("브라우저 창이 닫혔습니다.", raised.exception.detail)
        self.assertIsInstance(
            raised.exception.__cause__,
            BrowserWindowClosedError,
        )

    @patch.object(
        srt_router,
        "run_get_schedule",
        side_effect=KorailAccessBlockedError("코레일 자동화 제한"),
    )
    def test_get_schedule_returns_too_many_requests_when_blocked(
        self,
        _get_schedule,
    ):
        with self.assertRaises(HTTPException) as raised:
            srt_router.get_schedule(
                date="20260814",
                time="00",
                from_station="서울",
                to_station="부산",
            )

        self.assertEqual(429, raised.exception.status_code)
        self.assertEqual("코레일 자동화 제한", raised.exception.detail)

    @patch.object(
        srt_router,
        "run_macro_logic",
        side_effect=InvalidPhoneNumberError("예약대기 연락처 오류"),
    )
    def test_post_run_returns_unprocessable_phone_number(self, _run_macro):
        with self.assertRaises(HTTPException) as raised:
            srt_router.post_run(
                login_id="login-id",
                login_psw="login-password",
                from_station="서울",
                to_station="부산",
                date="20260814",
                time="00",
                reserve=True,
                reservation_phone="0101234",
                seats=[1],
            )

        self.assertEqual(422, raised.exception.status_code)
        self.assertEqual("예약대기 연락처 오류", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
