import os
import time
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
    NoAlertPresentException
)
from services.exceptions import InvalidStationNameError, InvalidDateError, InvalidDateFormatError  


station_list = ["수서", "동탄", "평택지제", "천안아산", "오송", "대전", "김천구미", "동대구",
                "신경주", "울산(통도사)", "부산", "공주", "익산", "정읍", "광주송정", "나주", "목포"]


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
        if self.dpt_stn not in station_list:
            raise InvalidStationNameError(f"출발역 오류. '{self.dpt_stn}' 은/는 목록에 없습니다.")
        if self.arr_stn not in station_list:
            raise InvalidStationNameError(f"도착역 오류. '{self.arr_stn}' 은/는 목록에 없습니다.")
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
        try:
            service = Service()
            self.driver = webdriver.Chrome(service=service)
        except WebDriverException:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service)

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
        menu_text = self.driver.find_element(By.CSS_SELECTOR, "#wrap > div.header.header-e > div.global.clear > div").text
        if "환영합니다" in menu_text:
            return True
        else:
            return False

    def go_search(self):
        self.driver.get('https://etk.srail.kr/hpg/hra/01/selectScheduleList.do')
        self.driver.implicitly_wait(5)

        elm_dpt_stn = self.driver.find_element(By.ID, 'dptRsStnCdNm')
        elm_dpt_stn.clear()
        elm_dpt_stn.send_keys(self.dpt_stn)

        elm_arr_stn = self.driver.find_element(By.ID, 'arvRsStnCdNm')
        elm_arr_stn.clear()
        elm_arr_stn.send_keys(self.arr_stn)

        elm_dpt_dt = self.driver.find_element(By.ID, "dptDt")
        self.driver.execute_script("arguments[0].setAttribute('style','display: True;')", elm_dpt_dt)
        Select(self.driver.find_element(By.ID, "dptDt")).select_by_value(self.dpt_dt)

        elm_dpt_tm = self.driver.find_element(By.ID, "dptTm")
        self.driver.execute_script("arguments[0].setAttribute('style','display: True;')", elm_dpt_tm)
        Select(self.driver.find_element(By.ID, "dptTm")).select_by_visible_text(self.dpt_tm)

        print("기차를 조회합니다")
        print(f"출발역:{self.dpt_stn} , 도착역:{self.arr_stn}\n날짜:{self.dpt_dt}, 시간: {self.dpt_tm}시 이후\n")
        target_indexs = ', '.join(f"{i}번" for i in self.target_index)
        print(f"{target_indexs} 기차를 예매합니다.")
        print(f"예약 대기 사용: {self.reserve_waiting}")

        self.driver.find_element(By.XPATH, "//input[@value='조회하기']").click()
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
            self.driver.execute_script("arguments[0].click();", submit)
            self.cnt_refresh += 1
            print(f"새로고침 {self.cnt_refresh}회")
            self.driver.implicitly_wait(10)
            time.sleep(1)
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

            time.sleep(randint(2, 4))
            self.refresh_result()            

    def run(self, login_id, login_psw):
        self.run_driver()
        self.set_log_info(login_id, login_psw)
        self.login()
        self.go_search()
        self.check_result()
        
        return self.is_booked

def get_schedule(dpt_stn, arr_stn, date, tm):
    items = []
    
    service = Service()
    opts = Options()
    opts.add_argument("--headless")
    driver = webdriver.Chrome(service=service, options=opts)
    
    try:
        driver.get('https://etk.srail.kr/hpg/hra/01/selectScheduleList.do')
        driver.implicitly_wait(5)

        elm_dpt_stn = driver.find_element(By.ID, 'dptRsStnCdNm')
        elm_dpt_stn.clear()
        elm_dpt_stn.send_keys(dpt_stn)

        elm_arr_stn = driver.find_element(By.ID, 'arvRsStnCdNm')
        elm_arr_stn.clear()
        elm_arr_stn.send_keys(arr_stn)

        elm_dpt_dt = driver.find_element(By.ID, "dptDt")
        driver.execute_script("arguments[0].setAttribute('style','display: True;')", elm_dpt_dt)
        Select(driver.find_element(By.ID, "dptDt")).select_by_value(date)

        elm_dpt_tm = driver.find_element(By.ID, "dptTm")
        driver.execute_script("arguments[0].setAttribute('style','display: True;')", elm_dpt_tm)
        Select(driver.find_element(By.ID, "dptTm")).select_by_visible_text(tm)

        driver.find_element(By.XPATH, "//input[@value='조회하기']").click()
        driver.implicitly_wait(5)
        time.sleep(1)
        
        rows = driver.find_elements(By.CSS_SELECTOR,
            "#result-form .tbl_wrap table tbody tr"
        )
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
        driver.quit()
            
    return items