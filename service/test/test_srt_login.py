import unittest
from unittest.mock import MagicMock, patch

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from service import ktx as ktx_module
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


@patch.object(ktx_module, "WebDriverWait", ImmediateWebDriverWait)
class LoginStateTest(unittest.TestCase):
    def setUp(self):
        self.ktx = ktx_module.KTX(
            dpt_stn="서울",
            arr_stn="부산",
            dpt_dt="20260814",
            dpt_tm="00",
            target_index=[1],
        )
        self.ktx.driver = MagicMock()

    def test_returns_true_when_logout_is_visible_after_redirect(self):
        self.ktx.driver.find_elements.return_value = [MagicMock()]
        self.ktx.driver.current_url = "https://www.korail.com/ticket/main"

        self.assertTrue(self.ktx.check_login())
        self.ktx.driver.find_elements.assert_called_once_with(
            By.XPATH,
            "//a[normalize-space()='로그아웃'] | "
            "//button[normalize-space()='로그아웃']",
        )

    def test_raises_when_welcome_message_is_absent(self):
        self.ktx.driver.find_elements.return_value = []

        with self.assertRaises(LoginFailedError):
            self.ktx.check_login()

    def test_raises_while_still_on_login_page(self):
        self.ktx.driver.find_elements.return_value = [MagicMock()]
        self.ktx.driver.current_url = ktx_module.LOGIN_URL

        with self.assertRaises(LoginFailedError):
            self.ktx.check_login()

    def test_run_stops_before_search_when_login_check_fails(self):
        self.ktx.run_driver = MagicMock()
        self.ktx.set_log_info = MagicMock()
        self.ktx.login = MagicMock()
        self.ktx.check_login = MagicMock(side_effect=LoginFailedError)
        self.ktx.go_search = MagicMock()

        with self.assertRaises(LoginFailedError):
            self.ktx.run("login-id", "login-password")

        self.ktx.go_search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
