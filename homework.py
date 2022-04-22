import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('pract_token')
TELEGRAM_TOKEN = os.getenv('tele_token')
TELEGRAM_CHAT_ID = os.getenv('chat_id')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
BOT = telegram.Bot(token=TELEGRAM_TOKEN)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s'
)

log = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
log.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        result = BOT.send_message(TELEGRAM_CHAT_ID, message)
        if result.text == message:
            log.info('Сообщение отправлено')
        return True
    except Exception as error:
        message = f'Сбой при отправке сообщения'
        log.error(message)
        return False


def get_api_answer(current_timestamp):
    """Осуществляет запрос к API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        response.raise_for_status()
        response = response.json()
        return response
    except requests.exceptions.HTTPError as error:
        if '404' in str(error):
            message = f'Сбой в работе программы: Эндпоинт {ENDPOINT} ' \
                      f'недоступен. Код ответа API: 404'
            log.error(message)
            send_message(BOT, message)
            log.info(f'Бот отправил сообщение {message}')
        else:
            message = f'Произошел сбои при запросе к эндпоинту'
            log.error(message)
    except Exception as error:
        message = f'Сбой в работе программы'
        log.error(message)
        log.error(error)
        send_message(BOT, message)
        return False


def check_response(response):
    """Проверяет ответ API на корректность."""
    if type(response) is not dict:
        message = f'Ответ API не является словарем'
        log.error(message)
        if 'homeworks' not in response.keys():
            message = f'Ответ API не содержит ключа homeworks'
            log.error(message)
            if len(response) == 0:
                message = f'Словарь значений пуст'
                log.error(message)
    homework = response.get('homeworks')
    return homework


def parse_status(homework):
    """Извлекает конкретный статус домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError as error:
        message = f'Ошибка доступа по ключу homework_name {error}'
        log.error(message)
    try:
        homework_status = homework['status']
    except KeyError as error:
        message = f'Ошибка доступа по ключу status {error}'
        log.error(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        verdict = 'Ошибка в статусе работы'
        log.error(verdict)
    return verdict


def check_tokens():
    """Проверяет доступность переменных окружения."""
    env_variables = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    try:
        for variable in env_variables:
            if variable in os.environ.values():
                pass
        return True
    except Exception as error:
        message = (
            f' Отсутствует обязательная переменная окружения: {variable} '
            f'Программа принудительно остановлена. ')
        log.critical(message)
        return False


def main():
    """Основная логика работы бота."""
    status = ''
    if check_tokens():
        current_timestamp = int(time.time())
        while True:
            response = get_api_answer(current_timestamp)
            try:
                homeworks = check_response(response)
                log.info(homeworks)
                if homeworks:
                    if homeworks[0].get('status') != status:
                        status = homeworks[0].get('status')
                        message = parse_status(homeworks[0])
                        send_message(BOT, message)
                    else:
                        log.debug('Статус проверки работы не изменился')
            except Exception as error:
                message = f'Ошибка в статусе проверки работы: {error}'
                log.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
