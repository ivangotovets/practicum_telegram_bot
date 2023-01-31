# Telegram Bot:
# @practicum_status_bot


import logging
import requests
import time
import telegram

from datetime import datetime
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from os import getenv
from sys import stdout, exit

from exceptions import (
    EndpointRequestError, InvalidJSONError,
    HTTPConnectionError, ResponseKeyError, UnexpectedStatusError
)

load_dotenv()

PRACTICUM_TOKEN = getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = getenv('TELEGRAM_CHAT_ID')
TOKENS = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

RETRY_PERIOD = 10 * 60
TODAY = int(time.time()) - RETRY_PERIOD

# Testing constants
# RETRY_PERIOD = 5
# TODAY = 0

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

NO_TOKENS_ERR_MSG = 'Нет переменных окружения: {}'
TELEGRAM_ERR_MSG = 'Ошибка отправки сообщения в Telegram'
ENDPOINT_ERR_MSG = ('Недоступен эндпоинт. \n'
                    'URL: {url}\n'
                    'Headers: {headers}\n'
                    'Status code: {status_code}\n'
                    'Reason: {reason}')
CONNECT_ERR_MSG = ('Ошибка соединения с сервером'
                   'URL: {url}\n'
                   'Headers: {headers}\n'
                   'Status code: {status_code}\n'
                   'Reason: {reason}')
HTTP_ERR_MSG = 'Ошибка HTTP'
RESP_KEY_ERR_MSG = "Отсутствуют ожидаемые ключи в ответе API"
WRONG_STATUS_ERR_MSG = "Неверный статус домашней работы"
TYPE_ERR_MSG = 'Ответ неверного типа'
SERV_RUN_ERR_MSG = 'Ошибка выполнения бота на сервере'

RESP_RECEIVED_MSG = 'Ответ сервера получен'
STAT_CHANGE_MSG = 'Изменился статус проверки работы "{0}". {1}'
JSON_ERR_MSG = 'Невалидный JSON'

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=(
        # logging.FileHandler("logger.log"),
        RotatingFileHandler(
            filename=__file__ + 'logger.log',
            maxBytes=40000000,
            backupCount=2
        ),
        logging.StreamHandler(stdout),
    )
)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    acc = []
    for token_name in TOKENS:
        if not globals().get(token_name):
            acc.append(token_name)
    if acc:
        raise SystemExit(NO_TOKENS_ERR_MSG.format(' '.join(acc)))


def send_message(bot, message):
    """Отправляет сообщение в Телеграм-чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError:
        logging.error(TELEGRAM_ERR_MSG)
        # просто снёс кастомный эксепш
        raise Exception(TELEGRAM_ERR_MSG)
    else:
        logging.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API и передает временную метку."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException:
        raise EndpointRequestError(ENDPOINT_ERR_MSG.format(
            url=response.url,
            headers=response.headers,
            status_code=response.status_code,
            reason=response.reason
        ))
    if response.status_code != 200:
        raise HTTPConnectionError(HTTP_ERR_MSG)
    logging.debug(RESP_RECEIVED_MSG)
    try:
        return response.json()
    except requests.exceptions.InvalidJSONError:
        raise InvalidJSONError(JSON_ERR_MSG.format(
            url=response.url,
            headers=response.headers,
            status_code=response.status_code,
            reason=response.reason

        ))


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    try:
        checked_data = response['homeworks']
    except KeyError:
        raise ResponseKeyError(RESP_KEY_ERR_MSG)
    api_response_correct = (
        isinstance(response['current_date'], int)
        and isinstance(response['homeworks'], list)
    )
    if not api_response_correct:
        raise TypeError(TYPE_ERR_MSG)
    return checked_data


def parse_status(homework):
    """Проверяет первый элемент из списка домашних работ."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        raise ResponseKeyError(RESP_KEY_ERR_MSG)
    try:
        verdict = HOMEWORK_VERDICTS[homework['status']]
    except KeyError:
        logging.error(WRONG_STATUS_ERR_MSG)
        raise UnexpectedStatusError
    return STAT_CHANGE_MSG.format(homework_name, verdict)


def process_api_response(response, bot, last_status):
    """Обработка ответа API."""
    homeworks = check_response(response)
    if len(homeworks) > 0:
        message = parse_status(homeworks[0])
        status = (f"{homeworks[0].get('status')}_"
                  f"{homeworks[0].get('date_updated')[:13]}")
        if status != last_status[0]:
            last_status[0] = status
            send_message(bot, message)
            logging.debug(message)
    else:
        logging.debug('Нет новых статусов')

    return last_status


def main():  # noqa: C901
    """Сделать запрос к API. Если есть обновления — получить статус."""
    try:
        check_tokens()
    except SystemExit as sys_e:
        logging.critical(sys_e)
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    send_message(bot, 'Бот запущен на сервере')
    api_errors = set()
    last_status = ['']
    while True:
        try:
            response = get_api_answer(TODAY)
            process_api_response(response, bot, last_status)
            time.sleep(RETRY_PERIOD)
        except TelegramSendingError as tel_error:
            logging.error(tel_error)
        except Exception as api_error:
            if api_error not in api_errors:
                api_errors.add(api_error)
                send_message(bot, api_error)
            logging.error(api_error)
        except KeyboardInterrupt:
            msg_exit = 'Прерывание пользователем'
            logging.critical(msg_exit)
            exit(msg_exit)
        except SystemExit:
            send_message(bot, SERV_RUN_ERR_MSG)
            logging.critical(SERV_RUN_ERR_MSG)
        # break на время отладки
        break


if __name__ == '__main__':
    main()
