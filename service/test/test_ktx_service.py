import unittest
from unittest.mock import MagicMock, call, patch
from urllib.parse import parse_qs, urlparse

from selenium.webdriver.common.by import By

from service import ktx
from service.exceptions import InvalidPhoneNumberError


class KtxSearchUrlTest(unittest.TestCase):
    def test_builds_ktx_only_result_url(self):
        url = ktx.build_search_url("서울", "부산", "20260910", "08")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual("/ticket/search/list", parsed.path)
        self.assertEqual(["서울"], query["txtGoStart"])
        self.assertEqual(["부산"], query["txtGoEnd"])
        self.assertEqual(["20260910"], query["txtGoAbrdDt"])
        self.assertEqual(["080000"], query["txtGoHour"])
        self.assertEqual(["100"], query["txtTrnGpCd"])
        self.assertEqual(["00"], query["selGoTrain"])
        self.assertEqual(["0001"], query["txtGoStartCode"])
        self.assertEqual(["0020"], query["txtGoEndCode"])


class KtxScheduleParserTest(unittest.TestCase):
    def make_snapshot(self, *, seat_text, seat_classes):
        return {
            "number_text": "KTX 123",
            "route_text": "서울 → 부산 (08:01 ~ 10:42)",
            "seat_text": seat_text,
            "seat_classes": seat_classes,
        }

    def test_loads_all_schedule_rows_with_one_webdriver_command(self):
        driver = MagicMock()
        expected = [
            self.make_snapshot(
                seat_text="일반실 예매",
                seat_classes=["price_box", "fl-l", "gen"],
            )
        ]
        driver.execute_script.return_value = expected

        result = ktx._load_schedule_snapshots(driver)

        self.assertEqual(expected, result)
        driver.execute_script.assert_called_once()
        self.assertEqual(
            ktx.SCHEDULE_RESULT_SELECTOR,
            driver.execute_script.call_args.args[1],
        )

    def test_parses_available_general_seat(self):
        item = ktx._extract_schedule_item(
            self.make_snapshot(
                seat_text="일반실 예매",
                seat_classes=["price_box", "fl-l", "gen"],
            )
        )

        self.assertEqual(
            {
                "train": 123,
                "depart": "08:01",
                "arrive": "10:42",
                "status": "예약가능",
            },
            item,
        )

    def test_parses_reservation_waiting(self):
        item = ktx._extract_schedule_item(
            self.make_snapshot(
                seat_text="일반실 예약대기",
                seat_classes=["price_box", "fl-l", "wait"],
            )
        )

        self.assertEqual("대기신청", item["status"])


class KtxOptionalNoticeTest(unittest.TestCase):
    def setUp(self):
        self.ktx = ktx.KTX(
            dpt_stn="서울",
            arr_stn="부산",
            dpt_dt="20260910",
            dpt_tm="08",
            target_index=[1],
        )
        self.ktx.driver = MagicMock()

    def test_closes_train_notice_regardless_of_message(self):
        confirm_button = MagicMock()
        notice = MagicMock()
        notice.is_displayed.side_effect = [True, False]
        notice.find_element.return_value = confirm_button
        self.ktx.driver.find_elements.return_value = [notice]

        self.assertTrue(self.ktx._dismiss_optional_train_notice())
        notice.find_element.assert_called_once_with(
            By.XPATH,
            ".//button[normalize-space()='확인']",
        )
        confirm_button.click.assert_called_once_with()

    def test_continues_when_notice_is_absent(self):
        self.ktx.driver.find_elements.return_value = []

        self.assertFalse(self.ktx._dismiss_optional_train_notice(timeout=0))


class KtxReservationWaitingFormTest(unittest.TestCase):
    def setUp(self):
        self.ktx = ktx.KTX(
            dpt_stn="서울",
            arr_stn="부산",
            dpt_dt="20260910",
            dpt_tm="08",
            target_index=[1],
            reserve_waiting=True,
            reservation_phone="010-2270-5172",
        )
        self.ktx.driver = MagicMock()

    def test_splits_formatted_phone_number_for_korail_inputs(self):
        self.assertEqual(
            ("010", "2270", "5172"),
            self.ktx.reservation_phone_parts,
        )

    def test_rejects_invalid_phone_number(self):
        with self.assertRaisesRegex(
            InvalidPhoneNumberError,
            "010-0000-0000",
        ):
            ktx.KTX(
                dpt_stn="서울",
                arr_stn="부산",
                dpt_dt="20260910",
                dpt_tm="08",
                target_index=[1],
                reserve_waiting=True,
                reservation_phone="010-1234",
            )

    @patch.object(ktx, "slow_send_keys")
    def test_fills_phone_part_one_character_at_a_time(self, slow_send_keys):
        wait = MagicMock()
        phone_input = MagicMock()
        wait.until.side_effect = [phone_input, True]

        self.ktx._fill_phone_part(wait, "phoneNumberNo2", "2270")

        phone_input.clear.assert_called_once_with()
        slow_send_keys.assert_called_once_with(phone_input, "2270")

    def test_checks_hidden_checkbox_through_its_label(self):
        wait = MagicMock()
        checkbox = MagicMock()
        checkbox.is_selected.return_value = False
        label = MagicMock()
        wait.until.side_effect = [checkbox, label, True]

        self.ktx._ensure_checkbox_selected(wait, "phoneNumChangeChecked")

        label.click.assert_called_once_with()

    @patch.object(ktx, "WebDriverWait")
    def test_submits_waiting_form_with_phone_and_consent(self, web_driver_wait):
        wait = web_driver_wait.return_value
        apply_button = MagicMock()
        wait.until.side_effect = [MagicMock(), apply_button, True]
        self.ktx._ensure_checkbox_selected = MagicMock()
        self.ktx._fill_phone_part = MagicMock()

        self.ktx._submit_reservation_wait()

        self.ktx._ensure_checkbox_selected.assert_has_calls(
            [
                call(wait, "phoneNumChangeChecked"),
                call(wait, "agreePersonnelInfoChecked"),
            ]
        )
        self.ktx._fill_phone_part.assert_has_calls(
            [
                call(wait, "phoneNumberNo1", "010"),
                call(wait, "phoneNumberNo2", "2270"),
                call(wait, "phoneNumberNo3", "5172"),
            ]
        )
        apply_button.click.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
