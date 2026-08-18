import unittest
from unittest.mock import MagicMock, patch

from selenium.common.exceptions import TimeoutException

from service import srt as srt_module


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

        self.assertTrue(srt_module.is_waiting_queue_visible(driver))

        _, selectors, result_selector = driver.calls[0]
        self.assertIn("#NetFunnel_Loading_Popup", selectors)
        self.assertEqual(srt_module.SCHEDULE_RESULT_SELECTOR, result_selector)

    def test_detects_queue_by_visible_text(self):
        driver = QueueStateDriver(
            (False, "현재 접속자가 많아 예상 대기 시간 10분", 0)
        )

        self.assertTrue(srt_module.is_waiting_queue_visible(driver))

    @patch.object(srt_module, "WebDriverWait", PollingWebDriverWait)
    def test_continues_immediately_when_result_is_ready_without_queue(self):
        driver = QueueStateDriver((False, "정상 조회 화면", 1))

        self.assertFalse(srt_module.wait_for_waiting_queue(driver))
        self.assertEqual(1, len(PollingWebDriverWait.calls))

    @patch.object(srt_module, "WebDriverWait", PollingWebDriverWait)
    def test_keeps_waiting_when_queue_ui_is_missed_until_result_is_ready(self):
        driver = QueueStateDriver(
            (False, "조회 중", 0),
            (False, "조회 중", 0),
            (False, "정상 조회 화면", 1),
        )

        self.assertFalse(srt_module.wait_for_waiting_queue(driver))
        self.assertEqual(3, len(driver.calls))

    @patch.object(srt_module, "WebDriverWait", PollingWebDriverWait)
    def test_waits_until_detected_queue_disappears(self):
        driver = QueueStateDriver(
            (True, "접속 대기 중", 0),
            (True, "접속 대기 중", 0),
            (False, "정상 조회 화면", 1),
        )

        self.assertTrue(srt_module.wait_for_waiting_queue(driver))
        self.assertEqual(
            [(
                driver,
                srt_module.WAITING_QUEUE_TIMEOUT,
                srt_module.WAITING_QUEUE_POLL_FREQUENCY,
            )],
            PollingWebDriverWait.calls,
        )
        self.assertEqual(3, len(driver.calls))

    @patch.object(srt_module, "WebDriverWait", PollingWebDriverWait)
    def test_raises_timeout_when_queue_never_disappears(self):
        driver = QueueStateDriver((True, "접속 대기 중", 0))

        with self.assertRaises(TimeoutException):
            srt_module.wait_for_waiting_queue(driver)


class WaitingQueueCallSiteTest(unittest.TestCase):
    def setUp(self):
        self.srt = srt_module.SRT(
            dpt_stn="수서",
            arr_stn="부산",
            dpt_dt="20260814",
            dpt_tm="00",
            target_index=[1],
        )
        self.driver = MagicMock()
        self.srt.driver = self.driver

    @patch.object(srt_module.time, "sleep")
    @patch.object(srt_module, "slow_select_keys")
    @patch.object(srt_module, "slow_send_keys")
    @patch.object(srt_module, "wait_for_waiting_queue")
    def test_go_search_waits_for_queue_after_submit(
        self,
        wait_for_queue,
        _slow_send_keys,
        _slow_select_keys,
        _sleep,
    ):
        self.srt.go_search()

        wait_for_queue.assert_called_once_with(self.driver)

    @patch.object(srt_module.time, "sleep")
    @patch.object(srt_module, "ActionChains")
    @patch.object(srt_module, "WebDriverWait")
    @patch.object(srt_module, "wait_for_waiting_queue")
    def test_refresh_result_waits_for_queue_after_submit(
        self,
        wait_for_queue,
        web_driver_wait,
        action_chains,
        _sleep,
    ):
        submit = MagicMock()
        web_driver_wait.return_value.until.return_value = submit
        actions = action_chains.return_value
        actions.send_keys.return_value = actions
        actions.pause.return_value = actions
        actions.move_to_element.return_value = actions
        actions.click.return_value = actions
        previous_row = MagicMock()
        self.driver.find_elements.return_value = [previous_row]

        self.srt.refresh_result()

        wait_for_queue.assert_called_once_with(
            self.driver,
            previous_rows=[previous_row],
        )

    @patch.object(srt_module.time, "sleep")
    @patch.object(srt_module, "slow_select_keys")
    @patch.object(srt_module, "slow_send_keys")
    @patch.object(srt_module, "wait_for_waiting_queue")
    @patch.object(srt_module.uc, "Chrome")
    @patch.object(srt_module, "install_arm_chromedriver")
    def test_get_schedule_waits_for_queue_after_submit(
        self,
        install_chromedriver,
        chrome,
        wait_for_queue,
        _slow_send_keys,
        _slow_select_keys,
        _sleep,
    ):
        install_chromedriver.return_value = "/tmp/chromedriver"
        driver = chrome.return_value
        driver.find_elements.return_value = []

        result = srt_module.get_schedule("수서", "부산", "20260814", "00")

        self.assertEqual([], result)
        wait_for_queue.assert_called_once_with(driver)
        driver.quit.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
