import os
import subprocess
import time

import random
import undetected_chromedriver as uc
from selenium.webdriver import ActionChains

from random import randint
from datetime import datetime
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ( 
    ElementClickInterceptedException, 
    StaleElementReferenceException, 
    WebDriverException, 
    NoAlertPresentException,
    TimeoutException,
)
from service.exceptions import (
    InvalidStationNameError,
    InvalidDateError,
    InvalidDateFormatError,
    LoginFailedError,
)


def install_arm_chromedriver():
    driver_path = ChromeDriverManager().install()
    uc.Patcher(executable_path=driver_path).auto()
    subprocess.run(
        ["codesign", "--force", "--sign", "-", driver_path],
        check=True,
    )
    return driver_path


WAITING_QUEUE_TIMEOUT = 1 * 60
WAITING_QUEUE_POLL_FREQUENCY = 0.5
LOGIN_WAIT_TIMEOUT = 15
SCHEDULE_RESULT_SELECTOR = "#result-form .tbl_wrap table tbody tr"
WAITING_QUEUE_SELECTORS = (
    "#NetFunnel_Loading_Popup",
    "[id^='NetFunnel_Loading_Popup_']",
    "iframe[id*='NetFunnel' i]",
    "iframe[src*='netfunnel' i]",
)
WAITING_QUEUE_TEXT_MARKERS = (
    "현재 접속자가 많아",
    "접속 대기 중",
    "기다리시면",
    "예상 대기시간",
    "대기자 수",
    "나의 대기 순서",
)


def get_schedule_page_state(driver):
    """Return the waiting-queue visibility and current schedule row count."""
    queue_element_visible, visible_text, result_row_count = driver.execute_script(
        """
        const selectors = arguments[0];
        const resultSelector = arguments[1];
        const isVisible = (element) => {
            const style = window.getComputedStyle(element);
            return style.display !== 'none'
                && style.visibility !== 'hidden'
                && Number(style.opacity) !== 0
                && element.getClientRects().length > 0;
        };

        const queueElements = Array.from(document.querySelectorAll(selectors));
        return [
            queueElements.some(isVisible),
            document.body?.innerText || '',
            document.querySelectorAll(resultSelector).length,
        ];
        """,
        ", ".join(WAITING_QUEUE_SELECTORS),
        SCHEDULE_RESULT_SELECTOR,
    )
    normalized_text = "".join(visible_text.split())
    has_queue_text = any(
        "".join(marker.split()) in normalized_text
        for marker in WAITING_QUEUE_TEXT_MARKERS
    )
    return bool(queue_element_visible or has_queue_text), result_row_count


def is_waiting_queue_visible(driver):
    """Return whether a visible NetFUNNEL waiting queue is on the page."""
    queue_visible, _ = get_schedule_page_state(driver)
    return queue_visible


def wait_for_waiting_queue(driver):
    """Wait until a queue clears and a new schedule result is ready."""
    queue_detected = False

    def schedule_is_ready(current_driver):
        nonlocal queue_detected

        queue_visible, result_row_count = get_schedule_page_state(current_driver)
        if queue_visible:
            queue_detected = True
            return False

        return result_row_count > 0

    WebDriverWait(
        driver,
        WAITING_QUEUE_TIMEOUT,
        poll_frequency=WAITING_QUEUE_POLL_FREQUENCY,
    ).until(schedule_is_ready)

    return queue_detected


class SRT:
    def __init__(self, dpt_stn, arr_stn, dpt_dt, dpt_tm, target_index, reserve_waiting=False):
        self.login_id = None
        self.login_psw = None

        self.dpt_stn = dpt_stn
        self.arr_stn = arr_stn
        self.dpt_dt = dpt_dt
        self.dpt_tm = dpt_tm
        self.target_index = target_index
        self.reserve_waiting = reserve_waiting
        self.driver = None

        self.is_booked = False
        self.cnt_refresh = 0

        self.check_input()

    def check_input(self):
        if not str(self.dpt_dt).isnumeric():
            raise InvalidDateFormatError("날짜는 숫자로만 이루어져야 합니다.")
        try:
            datetime.strptime(str(self.dpt_dt), '%Y%m%d')
        except ValueError:
            raise InvalidDateError("날짜가 잘못 되었습니다. YYYYMMDD 형식으로 입력해주세요.")

    def set_log_info(self, login_id, login_psw):
        self.login_id = login_id
        self.login_psw = login_psw

    def run_driver(self):
        driver_path = install_arm_chromedriver()
        try:
            self.driver = uc.Chrome(
                driver_executable_path=driver_path,
                headless=False,
            )
        except WebDriverException:
            self.driver = uc.Chrome(
                driver_executable_path=driver_path,
                headless=False,
            )

    def login(self):
        self.driver.get('https://etk.srail.kr/cmc/01/selectLoginForm.do')
        self.driver.implicitly_wait(15)
        self.driver.find_element(By.ID, 'srchDvNm01').send_keys(str(self.login_id))
        self.driver.find_element(By.ID, 'hmpgPwdCphd01').send_keys(str(self.login_psw))
        self.driver.find_element(
            By.CSS_SELECTOR,
            "input.submit.btn_pastel2.loginSubmit"
        ).click()
        self.driver.implicitly_wait(5)
        return self.driver

    def check_login(self):
        def has_welcome_message(driver):
            welcome_messages = driver.find_elements(
                By.CSS_SELECTOR,
                "#krds-header .header-actions > p.my-name",
            )
            return any(
                "님환영합니다!" in "".join(
                    (message.get_attribute("textContent") or "").split()
                )
                for message in welcome_messages
            )

        try:
            WebDriverWait(self.driver, LOGIN_WAIT_TIMEOUT).until(
                has_welcome_message
            )
        except TimeoutException as exc:
            raise LoginFailedError(
                "SRT 로그인 성공 여부를 확인할 수 없습니다."
            ) from exc

        return True

    def go_search(self):
        self.driver.implicitly_wait(4)
        self.driver.get('https://etk.srail.kr/hpg/hra/01/selectScheduleList.do')

        elm_dpt_stn = self.driver.find_element(By.ID, 'dptRsStnCdNm')
        elm_dpt_stn.clear()
        slow_send_keys(elm_dpt_stn, self.dpt_stn)
        time.sleep(0.7)

        elm_arr_stn = self.driver.find_element(By.ID, 'arvRsStnCdNm')
        elm_arr_stn.clear()
        slow_send_keys(elm_arr_stn, self.arr_stn)
        time.sleep(0.7)

        slow_select_keys(self.driver, "dptDt", self.dpt_dt, mode="value")
        slow_select_keys(self.driver, "dptTm", self.dpt_tm, mode="text")
        
        self.driver.find_element(By.ID, "trnGpCd300").click()
        
        print("기차를 조회합니다")
        print(f"출발역:{self.dpt_stn} , 도착역:{self.arr_stn}\n날짜:{self.dpt_dt}, 시간: {self.dpt_tm}시 이후\n")
        target_indexs = ', '.join(f"{i}번" for i in self.target_index)
        print(f"{target_indexs} 기차를 예매합니다.")
        print(f"예약 대기 사용: {self.reserve_waiting}")

        self.driver.find_element(By.XPATH, "//input[@value='조회하기']").click()
        wait_for_waiting_queue(self.driver)
        self.driver.implicitly_wait(5)
        time.sleep(1)

    def book_ticket(self, standard_seat, i):
        if "예약하기" in standard_seat:
            print("예약 가능 클릭")
            try:
                # 클릭 시도
                self.driver.find_element(
                    By.CSS_SELECTOR,f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(7) > a"
                ).click()
            except ElementClickInterceptedException as err:
                print("ElementClickInterceptedException 발생:", err)
                # 클릭이 가로막힐 경우 엔터키로 시도
                self.driver.find_element(
                    By.CSS_SELECTOR,f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(7) > a"
                ).send_keys(Keys.ENTER) 
            except StaleElementReferenceException:
                print("StaleElementReferenceException 발생: 다시 검색")
                self.driver.back()
                self.driver.implicitly_wait(5)
            finally:
                try:
                    alert = self.driver.switch_to.alert
                    print(f"Alert 감지: {alert.text}")
                    alert.accept()  # Alert 확인 (OK 클릭)
                    print("Alert 닫음")
                except NoAlertPresentException:
                    print("Alert 없음, 계속 진행")
                    
                time.sleep(0.5)
                self.driver.switch_to.active_element.send_keys(Keys.ENTER)
                self.driver.implicitly_wait(5)
                
            if self.driver.find_elements(By.ID, 'isFalseGotoMain'):
                self.is_booked = True
                print("예약 완료")
                return True
                
            else:
                print("잔여석 없음, 다시 검색")
                self.driver.back()
                self.driver.implicitly_wait(5)

    def refresh_result(self):
        wait = WebDriverWait(self.driver, 120)
        try:
            submit = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@value='조회하기']")))
            actions = ActionChains(self.driver)

            # 스크롤 활성화를 위해 ↓키 두 번
            actions.send_keys(Keys.ARROW_DOWN).pause(0.1)
            actions.send_keys(Keys.ARROW_DOWN).pause(0.1)
            # 버튼 포커스 후 Enter
            actions.move_to_element(submit).click().pause(0.1)
            actions.send_keys(Keys.ENTER).perform()
            
            self.cnt_refresh += 1
            print(f"새로고침 {self.cnt_refresh}회")
            self.driver.implicitly_wait(10)
            time.sleep(random.uniform(0.5, 1.5))

        except StaleElementReferenceException:
            print("요소가 더 이상 유효하지 않음. 다시 시도합니다.")
            self.refresh_result()

    def reserve_ticket(self, reservation, i):
        if "신청하기" in reservation:
            print("예약 대기 완료")
            self.driver.find_element(
                By.CSS_SELECTOR,f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(8) > a"
            ).click()
            self.is_booked = True
            return True

    def check_result(self):
        wait = WebDriverWait(self.driver, 120) 
        while not self.is_booked:
            for i in self.target_index:
                try:
                    standard_seat = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(7)"))).text
                    reservation = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"#result-form > fieldset > div.tbl_wrap.th_thead > table > tbody > tr:nth-child({i}) > td:nth-child(8)"))).text
                except StaleElementReferenceException:
                    standard_seat = "매진"
                    reservation = "매진"

                if self.book_ticket(standard_seat, i):
                    return True                   

                if self.reserve_waiting:
                    if self.reserve_ticket(reservation, i):
                        return True

            time.sleep(randint(1, 2))
            self.refresh_result()            

    def run(self, login_id, login_psw):
        self.run_driver()
        self.set_log_info(login_id, login_psw)
        self.login()
        self.check_login()
        self.go_search()
        self.check_result()
        
        return self.is_booked

def get_schedule(dpt_stn, arr_stn, date, tm):
    items = []

    driver_path = install_arm_chromedriver()
    driver = uc.Chrome(driver_executable_path=driver_path, headless=False)
    
    try:
        driver.implicitly_wait(4)
        driver.get('https://etk.srail.kr/hpg/hra/01/selectScheduleList.do')

        elm_dpt_stn = driver.find_element(By.ID, 'dptRsStnCdNm')
        elm_dpt_stn.clear()
        slow_send_keys(elm_dpt_stn, dpt_stn)
        time.sleep(0.7)

        elm_arr_stn = driver.find_element(By.ID, 'arvRsStnCdNm')
        elm_arr_stn.clear()
        slow_send_keys(elm_arr_stn, arr_stn)
        time.sleep(0.7)

        slow_select_keys(driver, "dptDt", date, mode="value")
        slow_select_keys(driver, "dptTm", tm, mode="text")
        
        driver.find_element(By.ID, "trnGpCd300").click()

        # 조회 버튼 클릭
        driver.find_element(By.XPATH, "//input[@value='조회하기']").click()
        
        rows = driver.find_elements(By.CSS_SELECTOR, SCHEDULE_RESULT_SELECTOR)
        for row in rows:
            # 열차번호: hidden input[name^=trnNo]
            trn_no = row.find_element(
                By.CSS_SELECTOR, "td.trnNo input[name^='trnNo']"
            ).get_attribute("value")

            # 시간 <em class="time">HH:MM</em> 두 개
            times = row.find_elements(By.CSS_SELECTOR, "td .time")
            depart = times[0].text
            arrive = times[1].text

            # 7번째 칸(a 태그)의 텍스트로 상태 구분
            txt7 = row.find_element(
                By.CSS_SELECTOR, "td:nth-child(7) a"
            ).text
            if "예약하기" in txt7:
                status = "예약가능"
            elif "신청하기" in txt7:
                status = "대기신청"
            else:
                status = "매진"

            items.append({
                "train":  int(trn_no),
                "depart": depart,
                "arrive": arrive,
                "status": status
            })
    finally:
        time.sleep(1.5)
        driver.quit()

    return items

def slow_send_keys(element, text, delay_range=(0.05, 0.1)):
    for ch in text:
        element.send_keys(ch)
        time.sleep(random.uniform(*delay_range))
        
def slow_select_keys(
    driver,
    element_id: str,
    target: str,
    mode: str = "value",
    delay_range=(0.05, 0.1)
):
    import pyautogui

    sel = driver.find_element(By.ID, element_id)
    options = sel.find_elements(By.TAG_NAME, "option")

    target_idx = None
    for i, opt in enumerate(options):
        value = opt.get_attribute("value") if mode == "value" else opt.text.strip()
        if value == target:
            target_idx = i
            break

    if target_idx is None:
        raise ValueError(f"{mode} '{target}' not found in <select id='{element_id}'>")

    cur_idx = next((i for i, o in enumerate(options) if o.is_selected()), 0)

    sel.click()
    time.sleep(random.uniform(*delay_range))

    delta = target_idx - cur_idx
    if delta == 0:
        pyautogui.press("enter")
        time.sleep(random.uniform(*delay_range))
        return

    key = "down" if delta > 0 else "up"

    for _ in range(abs(delta)):
        pyautogui.press(key)
        time.sleep(random.uniform(*delay_range))

    pyautogui.press("enter")
    time.sleep(1.5)
