import unittest
from unittest.mock import patch

from api.srt.controller import srt_controller


class SrtControllerNotificationTest(unittest.TestCase):
    @patch.object(srt_controller, "notify_booking_success")
    @patch.object(srt_controller, "SRT")
    def test_notifies_kakao_after_booking_success(self, srt_class, notify):
        srt_class.return_value.run.return_value = True

        result = srt_controller.run_macro_logic(
            login_id="login-id",
            login_psw="login-password",
            dpt_stn="수서",
            arr_stn="부산",
            dpt_dt="20260821",
            dpt_tm="08",
            target=[1],
            want_reserve=False,
        )

        self.assertTrue(result)
        notify.assert_called_once_with(
            from_station="수서",
            to_station="부산",
            departure_date="20260821",
            departure_time="08",
        )

    @patch.object(srt_controller, "notify_booking_success", return_value=False)
    @patch.object(srt_controller, "SRT")
    def test_notification_failure_does_not_change_booking_result(
        self,
        srt_class,
        _notify,
    ):
        srt_class.return_value.run.return_value = True

        result = srt_controller.run_macro_logic(
            login_id="login-id",
            login_psw="login-password",
            dpt_stn="수서",
            arr_stn="부산",
            dpt_dt="20260821",
            dpt_tm="08",
            target=[1],
            want_reserve=False,
        )

        self.assertTrue(result)

    @patch.object(srt_controller, "notify_booking_success")
    @patch.object(srt_controller, "SRT")
    def test_does_not_notify_when_booking_fails(self, srt_class, notify):
        srt_class.return_value.run.return_value = False

        result = srt_controller.run_macro_logic(
            login_id="login-id",
            login_psw="login-password",
            dpt_stn="수서",
            arr_stn="부산",
            dpt_dt="20260821",
            dpt_tm="08",
            target=[1],
            want_reserve=False,
        )

        self.assertFalse(result)
        notify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
