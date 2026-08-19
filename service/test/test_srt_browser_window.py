import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchWindowException,
)

from api.srt.endpoint import srt_router
from service import srt as srt_module
from service.exceptions import BrowserWindowClosedError


class BrowserWindowStateTest(unittest.TestCase):
    def setUp(self):
        self.srt = srt_module.SRT(
            dpt_stn="수서",
            arr_stn="부산",
            dpt_dt="20260814",
            dpt_tm="00",
            target_index=[1],
        )
        self.srt.driver = MagicMock()

    def prepare_run(self):
        self.srt.run_driver = MagicMock()
        self.srt.set_log_info = MagicMock()
        self.srt.login = MagicMock()
        self.srt.check_login = MagicMock()
        self.srt.go_search = MagicMock()
        self.srt.check_result = MagicMock()

    @patch("builtins.print")
    def test_run_stops_when_browser_window_is_closed(self, print_mock):
        self.prepare_run()
        self.srt.check_result.side_effect = NoSuchWindowException(
            "target window already closed"
        )

        with self.assertRaisesRegex(
            BrowserWindowClosedError,
            "브라우저 창이 닫혀 매크로를 종료합니다.",
        ) as raised:
            self.srt.run("login-id", "login-password")

        self.assertIsInstance(raised.exception.__cause__, NoSuchWindowException)
        print_mock.assert_called_once_with(
            "[매크로 종료] 브라우저 창이 닫혀 매크로를 종료합니다."
        )

    @patch("builtins.print")
    def test_run_stops_when_browser_session_is_invalid(self, print_mock):
        self.prepare_run()
        self.srt.login.side_effect = InvalidSessionIdException(
            "invalid session id"
        )

        with self.assertRaises(BrowserWindowClosedError) as raised:
            self.srt.run("login-id", "login-password")

        self.assertIsInstance(
            raised.exception.__cause__,
            InvalidSessionIdException,
        )
        self.srt.check_login.assert_not_called()
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
                from_station="수서",
                to_station="부산",
                date="20260814",
                time="00",
                reserve=False,
                seats=[1],
            )

        self.assertEqual(409, raised.exception.status_code)
        self.assertEqual("브라우저 창이 닫혔습니다.", raised.exception.detail)
        self.assertIsInstance(
            raised.exception.__cause__,
            BrowserWindowClosedError,
        )


if __name__ == "__main__":
    unittest.main()
