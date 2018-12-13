#This is a UI testing example with Selenium
#It uses Selenium Grid and sends tests in parallel to different browser types
# -*- coding: latin5 -*-
from __future__ import unicode_literals
import unittest
import wd.parallel
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class IsbankLogin(unittest.TestCase):


    def setUp(self):
        desired_capabilities = [
            webdriver.DesiredCapabilities.FIREFOX,
            webdriver.DesiredCapabilities.CHROME
        ]

        self.drivers = wd.parallel.Remote(
            desired_capabilities=desired_capabilities
        )
        self.driver = webdriver.Remote(
            command_executor="http://192.168.58.128:4444/wd/hub"
        )
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("--test-type")

    @wd.parallel.multiply
    def test_login_isbank_com_tr(self):
        driver = self.driver
        driver.get("http://www.isbank.com.tr/")
#        self.assertIn("Türkiye ?? Bankas? A.?.", driver.title)
        driver.save_screenshot('c:\\Screenshots\\Internet.png')
#        username = driver.find_element_by_id("login_login_username")
        internet_button = driver.find_element_by_xpath("//span[@class='box_font_big'][contains(text(),'Bireysel')]")
        internet_button.click()
        time.sleep(2)
        popuphandle = driver.window_handles[-1]
        driver.switch_to.window(popuphandle)
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@id='_ctl0_MusNoText']"))
        )

        musno_text = driver.find_element_by_xpath("//input[@id='_ctl0_MusNoText']")
        # musno_text.click()
        musno_text.send_keys("35435435")
        time.sleep(10)

    @wd.parallel.multiply
    def teardown(self):
        self.driver.close()


if __name__ == "__main__":
    unittest.main()