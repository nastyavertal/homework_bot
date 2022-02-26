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


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщений боту."""
    try:
        bot.sent_message(TELEGRAM_CHAT_ID, text=message)
        return message
    except Exception as error:
        logger.error(f'Error sending message: {error}')


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
        error_message = 'Endpoint is unavailable'
        logger.error(error_message)
        raise Exception(error_message)
    except JSONDecodeError:
        error_message = 'JSON conversion error'
        logger.error(error_message)
        raise Exception(error_message)
    except Exception as error:
        error_message = f'API error: {error}'
        logger.error(error_message)
        raise Exception(error_message)
    finally:
        logger.info('Function: get_api answer')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        error_message = 'API is not a dictionary'
        logger.error(error_message)
        raise TypeError(error_message)
    if 'homeworks' not in response.keys():
        error_message = 'There is no key homeworks'
        logger.error(error_message)
        raise KeyError(error_message)
    if not isinstance(response.get('homeworks'), list):
        error_message = 'API is not a list'
        logger.error(error_message)
        raise TypeError(error_message)
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из конкретной домашней работы  статус этой работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS.keys():
        error_message = 'Unknown homework status'
        logger.error(error_message)
        raise KeyError(error_message)

    verdict = HOMEWORK_VERDICTS[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность перемeнных окружения."""
    tokens = all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])
    return tokens


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_message = 'Token verification failed'
        logger.error(error_message)
        raise SystemExit()
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


if __name__ == '__main__':
    main()
