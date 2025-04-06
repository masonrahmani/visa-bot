from flask import Flask, render_template, jsonify
import threading
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
from telegram import Bot

app = Flask(__name__)

# Your original code (unchanged)
TOKEN = "7559619950:AAGQJBhye7ALCSJ7BPjwXtEjQ_Rtk1Oh1yo"
CHAT_ID = "7888816440"  # Replace with the actual chat ID
API_KEY = "f1a41b48a230c97e4a381ab033e1725d"
SITE_KEY = "6Le8dMkUAAAAAEzy7WYOlWbYh0eun-xK0j5aXt6W"
PAGE_URL = "https://evisatraveller.mfa.ir/en/request/applyrequest/"
DRIVER_PATH = "chromedriver.exe"

def solve_captcha():
    captcha_request_url = f"http://2captcha.com/in.php?key={API_KEY}&method=userrecaptcha&googlekey={SITE_KEY}&pageurl={PAGE_URL}&json=1"
    response = requests.get(captcha_request_url)
    request_result = response.json()

    if request_result["status"] != 1:
        print("❌ Failed to submit CAPTCHA to 2Captcha")
        return None

    captcha_id = request_result["request"]
    print(f"✅ CAPTCHA submitted, ID: {captcha_id}")

    time.sleep(20)
    while True:
        captcha_solution_url = f"http://2captcha.com/res.php?key={API_KEY}&action=get&id={captcha_id}&json=1"
        response = requests.get(captcha_solution_url)
        solution_result = response.json()

        if solution_result["status"] == 1:
            captcha_solution = solution_result["request"]
            print(f"🎉 CAPTCHA solved: {captcha_solution}")
            return captcha_solution
        
        print("⏳ Waiting for CAPTCHA to be solved...")
        time.sleep(5)
    return None

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.60 Safari/537.36")
    service = Service(executable_path=DRIVER_PATH)
    return webdriver.Chrome(service=service, options=chrome_options)

def fill_form(driver, form_data):
    try:
        wait = WebDriverWait(driver, 30)

        visa_select = wait.until(EC.presence_of_element_located((By.ID, "id_visa_type")))
        Select(visa_select).select_by_value(form_data["visa_type"])


        nationality_select = wait.until(EC.presence_of_element_located((By.ID, "id_nationality")))
        Select(nationality_select).select_by_value(form_data["nationality"])


        passport_select = wait.until(EC.presence_of_element_located((By.ID, "id_passport_type")))
        Select(passport_select).select_by_value(form_data["passport_type"])


        issuer_select = wait.until(EC.presence_of_element_located((By.ID, "id_issuer_agent")))
        Select(issuer_select).select_by_value(form_data["issuer_agent"])


        fields_filled_correctly = all([
            Select(driver.find_element(By.ID, "id_visa_type")).first_selected_option.get_attribute("value") == form_data["visa_type"],
            Select(driver.find_element(By.ID, "id_nationality")).first_selected_option.get_attribute("value") == form_data["nationality"],
            Select(driver.find_element(By.ID, "id_passport_type")).first_selected_option.get_attribute("value") == form_data["passport_type"],
            Select(driver.find_element(By.ID, "id_issuer_agent")).first_selected_option.get_attribute("value") == form_data["issuer_agent"]
        ])

        if not fields_filled_correctly:
            return False
        submit_button = wait.until(EC.element_to_be_clickable((By.ID, "first_step_submit_btn")))
        submit_button.click()
        print("✅ Form submitted")

        try:
            confirm_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'swal2-confirm') and contains(text(), 'Proceed')]")))
            confirm_button.click()

        except Exception as e:

            pass

        return True

    except Exception as e:
        print(f"❌ Error filling form: {str(e)}")
        return False

def check_submission_status(driver):
    try:
        wait = WebDriverWait(driver, 30)
        time.sleep(5)

        failure_alert_xpath = "//div[contains(@class, 'alert-danger-new') and contains(., 'Visa application list for your selected mission is full')]"
        alert_message = "Visa application list for your selected mission is full till further notice. Please try again in the next coming days."
        
        try:
            alert_element = wait.until(EC.presence_of_element_located((By.XPATH, failure_alert_xpath)))
            alert_text = alert_element.text.strip()
            if alert_message in alert_text:
                return False
            else:
                print("✅ Site is availabe to fill visa form")
                return True
        except:
            print("✅ Site is availabe to fill visa form")
            return True

    except Exception as e:
        print(f"❌ Error checking submission status: {str(e)}")
        return None


def refresh_captcha(driver):
    """Refresh captcha solution and update cookie"""
    print("🔄 Refreshing captcha solution...")
    captcha_solution = solve_captcha()
    if not captcha_solution:
        return False
    driver.get("https://evisatraveller.mfa.ir/en/request/")
    driver.add_cookie({
                'name': '__arcsrc',
                'value': captcha_solution,
                'domain': '.mfa.ir',
                'path': '/'
            })

    driver.get(PAGE_URL)
    return True

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_check', methods=['POST'])
def start_check():
    # Run the main function in a separate thread to avoid blocking
    threading.Thread(target=run_main).start()
    return jsonify({'status': 'success', 'message': 'Visa status check started'})

def run_main():
    # Create a new event loop for the thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Your original main function
    async def main():
        bot = Bot(token=TOKEN)
     
        form_data = {
            "visa_type": "11",     # Tourist
            "nationality": "21",   # Afghanistan
            "passport_type": "1",  # Ordinary
            "issuer_agent": "461"  # Embassy in Kabul
        }

        print("🔁 Starting periodic visa status check every 60 seconds...")
        captcha_solution = solve_captcha()
        if not captcha_solution:
            return
        driver = setup_driver()
        driver.get("https://evisatraveller.mfa.ir/en/request/")
        driver.add_cookie({
                    'name': '__arcsrc',
                    'value':  captcha_solution,
                    'domain': '.mfa.ir',
                    'path': '/'
                })

        driver.get(PAGE_URL)
        while True:
            try:
                success = fill_form(driver, form_data)
                if success:
                    submission_status = check_submission_status(driver)
                    if submission_status is True:
                        print("Visa list is available to fill the form")
                        await bot.send_message(chat_id=CHAT_ID, text="✅ Visa list is available to fill the form")
                        break  # Exit loop
                    elif submission_status is False:
                        await bot.send_message(chat_id=CHAT_ID, text="❌ Visa list full. Will retry in 60 seconds...")
                        print("❌ Visa list full. Will retry in 60 seconds...")
                    else:
                        refresh_captcha(driver)
                      
                else:
                    refresh_captcha(driver)

            except Exception as e:
                refresh_captcha(driver)
                print(f"🔥 Unexpected error: {str(e)}")
            finally:
                # driver.quit()
                await asyncio.sleep(20)  # Changed from time.sleep to asyncio.sleep

    # Run the main coroutine
    loop.run_until_complete(main())

if __name__ == '__main__':
    app.run(debug=True)