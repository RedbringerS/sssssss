import asyncio
import logging
import time
import asyncpg
from datetime import datetime
from seleniumbase import SB
from seleniumbase.common.exceptions import NoSuchElementException
from db_config import DB_CONFIG
from config import get_config
from handlers import send_info_message_to_subscribers

config = get_config()
VFS_URL = config.get('VFS', 'url')
EMAIL = config.get('VFS', 'email')
PASSWORD = config.get('VFS', 'password')
migris = config.get('PERSON', 'migris')
first_name = config.get('PERSON', 'First_Name')
last_name = config.get('PERSON', 'Last_Name')
gender = config.get('PERSON', 'gender')
date_of_birth = config.get('PERSON', 'date_of_birth')
national = config.get('PERSON', 'national')
phone_code = config.get('PERSON', 'phone_code')
number_phone = config.get('PERSON', 'number_phone')
email_person = config.get('PERSON', 'email_person')
passport_number = config.get('PERSON', 'passport_number')
passport_data_v = config.get('PERSON', 'passport_data_v')
passportExpirtyDate = config.get('PERSON', 'passportExpirtyDate')


async def save_execution_result_to_db(info_message, callback, bot):
    logging.info(f"Приступил к сохранению в БД : {info_message}")
    async with asyncpg.create_pool(**DB_CONFIG) as pool:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("INSERT INTO execution_results (result, execution_time) "
                                   "VALUES ($1, $2)", info_message, datetime.now())
    await callback(info_message, bot)


def open_the_turnstile_page(sb):
    logging.info("Открываю сайт VFS")
    sb.save_screenshot("s1.png")
    sb.driver.uc_open_with_reconnect(VFS_URL, reconnect_time=6.5)


def click_turnstile_and_verify(sb):
    logging.info("Ищу турникет")
    sb.save_screenshot("s2.png")
    sb.driver.uc_switch_to_frame("iframe")
    sb.driver.uc_click("span.mark")


def login(sb):
    logging.info("Начинаю процесс авторизации")
    sb.save_screenshot("s3.png")
    for _ in range(3):
        try:
            sb.press_keys("#mat-input-0", EMAIL)
            sb.press_keys("#mat-input-1", PASSWORD)
            if check_button_sigIn(sb):
                sb.driver.uc_click('button.mat-stroked-button')
                logging.info("Вход в аккаунт успешен")
                return True
            return False
        except NoSuchElementException:
            logging.error("Ошибка авторизации. Повторная попытка...")
    logging.info("Превышено максимальное количество попыток авторизации. Завершение скрипта.")
    return False


def check_button_sigIn(sb):
    logging.info("Проверка доступности кнопки входа")
    try:
        sb.wait_for_element_visible('button.mat-stroked-button:not([disabled])', timeout=10)
        logging.info("Кнопка 'Sign In' доступна.")
        return True
    except NoSuchElementException as e:
        logging.error(f"Кнопка 'Sign In' не найдена или заблокирована. {e}")
        return False


def check_slot(sb):
    logging.info("Проверка свободного слота")
    try:
        accept_cookie_button = sb.wait_for_element("#onetrust-accept-btn-handler", timeout=5)
        sb.execute_script("arguments[0].scrollIntoView(true);", accept_cookie_button)
        sb.execute_script("arguments[0].click();", accept_cookie_button)
        logging.info("Куки пройдены")
    except NoSuchElementException:
        logging.error("Кнопка принятия куков не найдена в течение 10 секунд. Продолжаем выполнение скрипта.")

    sb.driver.uc_click('div.position-relative button.mat-raised-button:last-child')

    for _ in range(3):
        try:
            mat_select = sb.driver.find_element('mat-select[formcontrolname="selectedSubvisaCategory"]')
            sb.driver.execute_script("arguments[0].scrollIntoView();", mat_select)
            time.sleep(1)
            mat_select.click()
            sb.wait_for_element_visible('mat-option', timeout=10)
            sb.driver.click('mat-option')
            # sb.driver.click('mat-option:nth-child(2)')

        except Exception as e:
            logging.error(f"Произошла ошибка: {e}")

    try:
        info_message = sb.get_text("div.alert.alert-info.border-0.rounded-0", timeout=10)
        logging.info(f"Сообщение: {info_message}")
        return info_message
    except NoSuchElementException as e:
        info_message = f"Ошибка выполнения {e}"
        logging.error(info_message)
        return info_message


def check_continue_button(sb):
    logging.info("Проверка доступности кнопки запись")
    try:
        sb.wait_for_element_visible('button.mat-raised-button:not([disabled])', timeout=5)
        logging.info("Кнопка 'Continue' доступна.")
        return True
    except NoSuchElementException:
        logging.error("Кнопка 'Continue' не найдена или заблокирована.")
        return False


def record_person(sb):
    logging.info("Запись на подачу")

    sb.driver.uc_click('button.mat-raised-button')

    sb.press_keys("#mat-input-2", migris)  # MIGRIS
    sb.press_keys("#mat-input-3", first_name)  # First_Name
    sb.press_keys("#mat-input-4", last_name)  # Last_Name

    sb.click('#mat-select-6')
    sb.wait_for_element_visible('mat-option', timeout=5)
    sb.click(f'//mat-option[contains(.,"{gender}")]')

    sb.click('mat-select[aria-labelledby="mat-select-value-9"]')
    sb.wait_for_element_visible('mat-option', timeout=5)
    sb.click(f'//mat-option[contains(.,"{national}")]')

    sb.click('#dateOfBirth')
    sb.press_keys('#dateOfBirth', date_of_birth)

    sb.press_keys("#mat-input-5", passport_number)

    sb.click('#passportExpirtyDate')
    sb.press_keys('#passportExpirtyDate', passportExpirtyDate)

    sb.click('#mat-input-6')

    sb.press_keys("#mat-input-6", phone_code)
    sb.press_keys("#mat-input-7", number_phone)
    sb.press_keys("#mat-input-8", email_person)

    time.sleep(2)
    sb.click('button.mat-stroked-button.mat-button-base.btn.btn-block.btn-brand-orange.mat-btn-lg')
    time.sleep(1000)


async def vfs_trpl(callback, bot):
    with SB(uc=True, test=True) as sb:
        try:
            open_the_turnstile_page(sb)
            try:
                click_turnstile_and_verify(sb)
            except Exception:
                open_the_turnstile_page(sb)
                click_turnstile_and_verify(sb)

            if login(sb):
                info_message = check_slot(sb)
                await save_execution_result_to_db(info_message, callback, bot)
                if check_continue_button(sb):
                    record_person(sb)
                return info_message
            info_message = "Ошибка авторизации."
            return info_message

        except Exception as e:
            info_message = "Ошибка выполнения скрипта"
            logging.error(f"info_message: {e}")
            await save_execution_result_to_db(info_message, callback, bot)
            return info_message


async def run_vfs_trpl(callback, bot):
    logging.info("Starting VFS")
    while True:
        info_message = await vfs_trpl(send_info_message_to_subscribers, bot)
        logging.info(f"Получено информационное сообщение: {info_message}")
        logging.info("Повторный запуск через 5 минут")
        await asyncio.sleep(600)
