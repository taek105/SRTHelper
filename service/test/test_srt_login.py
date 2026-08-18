import unittest
from unittest.mock import MagicMock, patch

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from service import srt as srt_module
from service.exceptions import LoginFailedError


class ImmediateWebDriverWait:
    def __init__(self, driver, timeout):
        self.driver = driver
        self.timeout = timeout

    def until(self, condition):
        result = condition(self.driver)
        if result:
            return result
        raise TimeoutException("login welcome message was not found")


@patch.object(srt_module, "WebDriverWait", ImmediateWebDriverWait)
class LoginStateTest(unittest.TestCase):
    def setUp(self):
        self.srt = srt_module.SRT(
            dpt_stn="수서",
            arr_stn="부산",
            dpt_dt="20260814",
            dpt_tm="00",
            target_index=[1],
        )
        self.srt.driver = MagicMock()

    def test_returns_true_for_header_welcome_message(self):
        welcome_message = MagicMock()
        welcome_message.get_attribute.return_value = "\n  테스트 사용자 님 환영합니다!\n"
        self.srt.driver.find_elements.return_value = [welcome_message]

        self.assertTrue(self.srt.check_login())
        self.srt.driver.find_elements.assert_called_once_with(
            By.CSS_SELECTOR,
            "#krds-header .header-actions > p.my-name",
        )

    def test_raises_when_welcome_message_is_absent(self):
        self.srt.driver.find_elements.return_value = []

        with self.assertRaises(LoginFailedError):
            self.srt.check_login()

    def test_raises_for_my_name_without_welcome_text(self):
        dropdown_name = MagicMock()
        dropdown_name.get_attribute.return_value = "테스트 사용자"
        self.srt.driver.find_elements.return_value = [dropdown_name]

        with self.assertRaises(LoginFailedError):
            self.srt.check_login()

    def test_run_stops_before_search_when_login_check_fails(self):
        self.srt.run_driver = MagicMock()
        self.srt.set_log_info = MagicMock()
        self.srt.login = MagicMock()
        self.srt.check_login = MagicMock(side_effect=LoginFailedError)
        self.srt.go_search = MagicMock()

        with self.assertRaises(LoginFailedError):
            self.srt.run("login-id", "login-password")

        self.srt.go_search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
