import unittest
from unittest.mock import MagicMock, patch

from selenium.common.exceptions import TimeoutException

from service import ktx as ktx_module
from service.exceptions import KorailAccessBlockedError


class QueueStateDriver:
    def __init__(self, *states):
        self.states = iter(states)
        self.last_state = (False, "", 0)
        self.calls = []

    def execute_script(self, script, selectors, result_selector):
        self.calls.append((script, selectors, result_selector))
        try:
            self.last_state = next(self.states)
        except StopIteration:
            pass
        return self.last_state


class PollingWebDriverWait:
    calls = []

    def __init__(self, driver, timeout, poll_frequency):
        self.driver = driver
        self.timeout = timeout
        self.poll_frequency = poll_frequency
        self.__class__.calls.append((driver, timeout, poll_frequency))

    def until(self, condition):
        for _ in range(5):
            result = condition(self.driver)
            if result:
                return result
        raise TimeoutException("waiting queue did not disappear")


class WaitingQueueTest(unittest.TestCase):
    def setUp(self):
        PollingWebDriverWait.calls.clear()

    def test_detects_visible_netfunnel_queue(self):
        driver = QueueStateDriver((True, "", 0))

        self.assertTrue(ktx_module.is_waiting_queue_visible(driver))

        _, selectors, result_selector = driver.calls[0]
        self.assertIn("#NetFunnel_Loading_Popup", selectors)
        self.assertEqual(ktx_module.SCHEDULE_READY_SELECTOR, result_selector)

    def test_detects_queue_by_visible_text(self):
        driver = QueueStateDriver(
            (False, "현재 접속자가 많아 예상 대기 시간 10분", 0)
        )

        self.assertTrue(ktx_module.is_waiting_queue_visible(driver))

    def test_raises_when_korail_blocks_automation(self):
        driver = QueueStateDriver(
            (
                False,
                (
                    "매크로, 개발자도구 등 미허가 도구 사용 시 이용이 제한될 수 "
                    "있습니다. CODE : -4003"
                ),
                1,
            )
        )

        with self.assertRaises(KorailAccessBlockedError):
            ktx_module.get_schedule_page_state(driver)

    @patch.object(ktx_module, "WebDriverWait", PollingWebDriverWait)
    def test_continues_immediately_when_result_is_ready_without_queue(self):
        driver = QueueStateDriver((False, "정상 조회 화면", 1))

        self.assertFalse(ktx_module.wait_for_waiting_queue(driver))
        self.assertEqual(1, len(PollingWebDriverWait.calls))

    @patch.object(ktx_module, "WebDriverWait", PollingWebDriverWait)
    def test_keeps_waiting_when_queue_ui_is_missed_until_result_is_ready(self):
        driver = QueueStateDriver(
            (False, "조회 중", 0),
            (False, "조회 중", 0),
            (False, "정상 조회 화면", 1),
        )

        self.assertFalse(ktx_module.wait_for_waiting_queue(driver))
        self.assertEqual(3, len(driver.calls))

    @patch.object(ktx_module, "WebDriverWait", PollingWebDriverWait)
    def test_waits_until_detected_queue_disappears(self):
        driver = QueueStateDriver(
            (True, "접속 대기 중", 0),
            (True, "접속 대기 중", 0),
            (False, "정상 조회 화면", 1),
        )

        self.assertTrue(ktx_module.wait_for_waiting_queue(driver))
        self.assertEqual(
            [(
                driver,
                ktx_module.WAITING_QUEUE_TIMEOUT,
                ktx_module.WAITING_QUEUE_POLL_FREQUENCY,
            )],
            PollingWebDriverWait.calls,
        )
        self.assertEqual(3, len(driver.calls))

    @patch.object(ktx_module, "WebDriverWait", PollingWebDriverWait)
    def test_raises_timeout_when_queue_never_disappears(self):
        driver = QueueStateDriver((True, "접속 대기 중", 0))

        with self.assertRaises(TimeoutException):
            ktx_module.wait_for_waiting_queue(driver)


class WaitingQueueCallSiteTest(unittest.TestCase):
    def setUp(self):
        self.ktx = ktx_module.KTX(
            dpt_stn="서울",
            arr_stn="부산",
            dpt_dt="20260814",
            dpt_tm="00",
            target_index=[1],
        )
        self.driver = MagicMock()
        self.ktx.driver = self.driver

    @patch.object(ktx_module.time, "sleep")
    @patch.object(ktx_module, "wait_for_waiting_queue")
    def test_go_search_waits_for_queue_after_submit(
        self,
        wait_for_queue,
        _sleep,
    ):
        self.ktx.go_search()

        wait_for_queue.assert_called_once_with(self.driver)
        self.driver.get.assert_called_once_with(self.ktx.search_url)

    @patch.object(ktx_module.time, "sleep")
    @patch.object(ktx_module, "wait_for_waiting_queue")
    def test_refresh_result_waits_for_new_result(
        self,
        wait_for_queue,
        _sleep,
    ):
        self.ktx.refresh_result()

        self.driver.refresh.assert_called_once_with()
        wait_for_queue.assert_called_once_with(self.driver)

    @patch.object(ktx_module.time, "sleep")
    @patch.object(ktx_module.KTX, "_open_search_page", autospec=True)
    @patch.object(
        ktx_module.KTX,
        "_start_authenticated_session",
        autospec=True,
    )
    def test_get_schedule_waits_for_result(
        self,
        start_authenticated_session,
        open_search_page,
        _sleep,
    ):
        driver = MagicMock()
        driver.execute_script.return_value = []

        def attach_driver(instance, _login_id, _login_psw):
            instance.driver = driver

        start_authenticated_session.side_effect = attach_driver

        result = ktx_module.get_schedule(
            "login-id",
            "login-password",
            "서울",
            "부산",
            "20260814",
            "00",
        )

        self.assertEqual([], result)
        authenticated_session = start_authenticated_session.call_args.args[0]
        start_authenticated_session.assert_called_once_with(
            authenticated_session,
            "login-id",
            "login-password",
        )
        open_search_page.assert_called_once_with(authenticated_session)
        driver.execute_script.assert_called_once()
        driver.find_elements.assert_not_called()
        driver.quit.assert_called_once_with()

if __name__ == "__main__":
    unittest.main()
