import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions
import settings

load_dotenv()

logging.basicConfig(
    format='%(asctime)s: %(levelname)s - %(message)s - %(name)s',
    level=logging.DEBUG,
    filename='homework_bot.log',
    filemode='a'
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


def send_message(bot, message):
    """Sending a message to the Telegram chat."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение было отправлено')
    except Exception as exc:
        logger.error(f'Не удалось отправить сообщение: {exc}')


def get_api_answer(current_timestamp):
    """Getting a response from an API request."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            settings.ENDPOINT,
            headers=settings.HEADERS,
            params=params
        )
    except Exception as exc:
        logging.error(f'Произошла ошибка: {exc}')
    if response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
        message = ('Внутренняя ошибка сервера')
        raise requests.exceptions.RequestException(message)
    if response.status_code != HTTPStatus.OK:
        message = (f'Произошел сбой.'
                   f'Запрос к эндпоинту вернул код {response.status_code}')
        raise requests.exceptions.RequestException(message)
    try:
        return response.json()
    except ValueError:
        logger.error('Ответ получен не в JSON-формате')
        return {}


def check_response(response):
    """Checking the type of received response."""
    if not isinstance(response, dict):
        message = 'Неправильный тип полученного ответа'
        logging.error(message)
        raise TypeError(message)
    if response.get('homeworks') is None:
        message = 'В полученном ответе отсутствует ключ homeworks'
        logging.error(message)
        raise exceptions.MissingHomeworkKey(message)
    if not isinstance(response['homeworks'], list):
        message = 'Перечень домашних работ должен содержаться в списке'
        logging.error(message)
        raise exceptions.HomeworksNotInList(message)
    return response.get('homeworks')


def parse_status(homework):
    """Extracting the homework status from homework info."""
    if not (('homework_name' in homework) and ('status' in homework)):
        logging.error('Отсутствуют имя и статус домашней работы')
        print(homework)
    if homework == []:
        return {}
    else:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        if homework_status not in settings.HOMEWORK_STATUSES:
            message = 'Статус домашней работы отличается от ожидаемого'
            logging.error(message)
            raise KeyError(message)
        verdict = settings.HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Checking for the presence of all required environmental variables."""
    envvars = [PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]
    for envvar in envvars:
        if envvar is None:
            logger.critical(f'Отсутствует переменная окружения: {envvar}')
            return False
    return True


def main():
    """The main logic of bot work."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                send_message(bot, parse_status(homeworks[0]))
            else:
                logger.debug('Статус не изменился')
            current_timestamp = current_timestamp
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            try:
                send_message(bot, message)
            except Exception:
                not_send_message = 'Не удалось отправить сообщение об ошибке'
                logging.error(not_send_message)
        finally:
            time.sleep(settings.RETRY_TIME)


if __name__ == '__main__':
    main()
