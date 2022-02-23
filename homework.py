import logging
import os
import time
from http import HTTPStatus
from json import JSONDecodeError

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

LIST_ERRORS = []

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='program.log',
    filemode='w',
)
logger = logging.getLogger(__name__)


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщений боту."""
    try:
        bot.sent_message(TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        error_message = f'Error sending message: {error}'
        logger.error(message)
        if error_message not in LIST_ERRORS:
            send_message(bot, error_message)
            LIST_ERRORS.append(error_message)


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            message = 'API unavailable: status code is not 200'
            logger.error(message)
            raise Exception(message)
        return response.json()
    except requests.exceptions.RequestException:
        logger.error('Endpoint is unavailable')
        raise Exception('Endpoint is unavailable')
    except JSONDecodeError:
        logger.error('JSON conversion error')
        raise Exception('JSON conversion error')
    except Exception as error:
        logger.error(f'API error: {error}')
        raise Exception(f'API error: {error}')
    finally:
        logger.info('Function: get_api answer')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        logger.error('API is not a dictionary')
        raise TypeError('API is not a dictionary')
    if 'homeworks' not in response.keys():
        logger.error('There is no key homeworks')
        raise KeyError('There is no key homeworks')
    if not isinstance(response.get('homeworks'), list):
        logger.error('API is not a list')
        raise TypeError('API is not a list')
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из конкретной домашней работе статус этой работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность перемeнных окружения."""
    if TELEGRAM_TOKEN is None or PRACTICUM_TOKEN is None or \
            TELEGRAM_CHAT_ID is None:
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_message = 'Token verification failed'
        logger.error(error_message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                send_message(bot, parse_status(homework[0]))
            current_timestamp = response.get('current_date',
                                             current_timestamp)
            time.sleep(RETRY_TIME)

        except Exception as error:
            error_message = f'Program crash: {error}'
            logger.error(error_message)
            if error_message not in LIST_ERRORS:
                send_message(bot, error_message)
                LIST_ERRORS.append(error_message)
            time.sleep(RETRY_TIME)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
