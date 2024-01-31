import psycopg2
from datetime import datetime
import logging
from telebot import types
import telebot
import sys
import os

logging.basicConfig(level=logging.INFO)
with open('Token.txt', 'r') as f:
    token = f.read().strip()
bot = telebot.TeleBot(token)
user_states = {}
support_chat_id = -1002108772616

"""Подключение к базе данных."""
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host="127.0.0.1",
            database="postgres",
            user="postgres",
            password="1111",
            port="5432"
        )
        return conn
    except Exception as e:
        logging.error(f'Error in get_db_connection: {e}')
        return None, None

"""Функция для удаления медиа из директории после изменения статуса тикета."""
def cleanup_media_files(ticket_id):
    media_dir = 'media'
    for root, dirs, files in os.walk(media_dir):
        for file in files:
            if str(ticket_id) in file:
                file_path = os.path.join(root, file)
                os.remove(file_path)



"""Отправляем последний запрос в чат поддержки из базы данных."""
def send_last_ticket_to_support_chat(ticket_id, contacts, description, op, status, creation_time, media=None):
    try:
        keyboard = types.InlineKeyboardMarkup()
        button_change_status = types.InlineKeyboardButton(text="Изменить статус тикета", callback_data=f"respond_{ticket_id}")
        keyboard.add(button_change_status)

        message = f"Новый запрос:\n"
        message += f"ID запроса: {ticket_id}\n"
        message += f"Контакты: {contacts}\n"
        message += f"ОП: {op}\n"
        message += f"Описание: {description}\n"
        message += f"Статус: {'Открыт' if status else 'Закрыт'}\n"
        message += f"Время создания: {creation_time}"

        if media:
            media_files = []
            for media_file in media:
                with open(media_file, 'rb') as media_file_obj:
                    media_files.append(types.InputMediaPhoto(media_file_obj))
                    bot.send_media_group(support_chat_id, media_files)
                    bot.send_message(support_chat_id, message, reply_markup=keyboard)

        else:
            bot.send_message(support_chat_id, message, reply_markup=keyboard)
    except Exception as e:
        logging.error(f'Error in send_last_ticket_to_support_chat: {e}')

"""Функция для получения user id  по тикет id из базы данных."""
def get_user_id_by_ticket_id(ticket_id):
    conn = get_db_connection()
    if not conn:
        return None

    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM trables WHERE ticket_id = %s", (ticket_id,))
        user_id = cur.fetchone()
        if user_id:
            return user_id[0]
        else:
            return None

"""Вывод всех тикетов пользователю."""
def show_user_tickets(message):
    user_id = message.chat.id
    conn = get_db_connection()
    if not conn:
        return

    with conn.cursor() as cur:
        cur.execute("SELECT ticket_id, contacts, description, op, status FROM trables WHERE user_id = %s", (user_id,))
        tickets = cur.fetchall()

    if not tickets:
        bot.send_message(user_id, 'У вас нет активных запросов.')
        return

    response = 'Ваши запросы:\n\n'
    for ticket in tickets:
        ticket_id, contacts, description, op, status = ticket
        status_text = 'Открыт' if status else 'Закрыт'
        response += f'ID запроса: {ticket_id}\n'
        response += f'Контакты: {contacts}\n'
        response += f'ОП: {op}\n'
        response += f'Описание: {description}\n'
        response += f'Статус: {status_text}\n\n'

    bot.send_message(user_id, response)

"""Добавляем тикет в базу данных."""
def add_data_to_db(user_id, contacts, description, op, media=None):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Создать запрос')
    button2 = types.KeyboardButton('Мои запросы')
    keyboard.add(button1, button2)
    try:
        conn = get_db_connection()
        if not conn:
            return

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO trables (user_id, description, op, contacts, status, media) VALUES (%s, %s, %s, %s, %s, %s) RETURNING ticket_id",
                (user_id, description, op, contacts, True, media)
            )
            conn.commit()
            ticket_id = cur.fetchone()[0]
            creation_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            bot.send_message(user_id, f'Запрос успешно создан. Ваш ID запроса: {ticket_id}',reply_markup=keyboard)
            send_last_ticket_to_support_chat(ticket_id, contacts, description, op, True, creation_time, media)
    except Exception as e:
        logging.error(f'Error in create_ticket: {e}')

"""Запрашваем у юзера его контакты."""
def process_contacts(message):
    user_id = message.chat.id
    contacts = message.text
    user_states[user_id]['contacts'] = contacts
    bot.send_message(user_id, 'Опишите вашу проблему')
    bot.register_next_step_handler(message, process_description, user_id)
"""Запрашиваем у юзера описание его проблемы."""
def process_description(message, user_id):
    user_states[user_id]['description'] = message.text
    bot.send_message(user_id, 'Напишите ваш объект продаж')
    bot.register_next_step_handler(message, process_OP, user_id)
"""Запрашиваем у юзера ОП."""
def process_OP(message, user_id):
    user_states[user_id]['op'] = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Нет медиа')
    keyboard.add(button1)
    bot.send_message(user_id, 'Отправьте медиа файлы',reply_markup=keyboard)
    bot.register_next_step_handler(message, process_media_and_confirmation, user_id)

"""Запрашиваем у юзера медиа файлы и обрабатываем их,если файлы отсутствуют добавляем данные в базу оставляя media = None."""
def process_media_and_confirmation(message, user_id):
    user_states[user_id]['media'] = []

    if message.content_type == 'photo' or message.content_type == 'video':
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        media_path = os.path.join(os.path.abspath('.'), 'media', file_info.file_path)

        if not os.path.exists(os.path.dirname(media_path)):
            os.makedirs(os.path.dirname(media_path))

        with open(media_path, 'wb') as media_file:
            media_file.write(downloaded_file)
        user_states[user_id]['media'].append(media_path)
        add_data_to_db(user_id, user_states[user_id]['contacts'], user_states[user_id]['description'], user_states[user_id]['op'], user_states[user_id]['media'])
        del user_states[user_id]
    elif message.content_type == 'document' and message.document.mime_type.startswith('image/') or message.content_type == 'document' and message.document.mime_type.startswith('video/'):
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        media_path = os.path.join(os.path.abspath('.'), 'media', file_info.file_path)
    elif message.text == 'Нет медиа':
        add_data_to_db(user_id, user_states[user_id]['contacts'], user_states[user_id]['description'],user_states[user_id]['op'], user_states[user_id]['media'])
        del user_states[user_id]


        if not os.path.exists(os.path.dirname(media_path)):
            os.makedirs(os.path.dirname(media_path))

        with open(media_path, 'wb') as media_file:
            media_file.write(downloaded_file)
        user_states[user_id]['media'].append(media_path)
        add_data_to_db(user_id, user_states[user_id]['contacts'], user_states[user_id]['description'], user_states[user_id]['op'], user_states[user_id]['media'])
        del user_states[user_id]


    if user_states[user_id]['media']:
        add_data_to_db(user_id, user_states[user_id]['contacts'], user_states[user_id]['description'], user_states[user_id]['op'], user_states[user_id]['media'])
        del user_states[user_id]



@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    user_states[user_id] = {}

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('Создать запрос')
    button2 = types.KeyboardButton('Мои запросы')
    keyboard.add(button1, button2)
    bot.reply_to(message, 'Привет это бот поддержки', reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == 'Создать запрос')
def create_ticket(message):
    user_id = message.chat.id
    user_states[user_id] = {}

    bot.send_message(user_id, 'Напишите ваши контакты:')
    bot.register_next_step_handler(message, process_contacts)


@bot.message_handler(func=lambda message: message.text == 'Мои запросы')
def handle_start(message):
    user_id = message.chat.id
    user_states[user_id] = {}
    show_user_tickets(message)
"""Функция обработки нажатия на кнопку изменения статуса тикета."""
@bot.callback_query_handler(func=lambda call: call.data.startswith('respond_'))
def handle_respond_button(call):
    ticket_id = int(call.data.split('_')[1])
    user_who_clicked_button = call.from_user.username
    bot.answer_callback_query(callback_query_id=call.id, text='Статус заявки изменен на "Завершен"', show_alert=True)
    user_id = get_user_id_by_ticket_id(ticket_id)
    if user_id:
        conn = get_db_connection()
        if not conn:
            return

        with conn.cursor() as cur:
            cur.execute("UPDATE trables SET status = FALSE WHERE ticket_id = %s", (ticket_id,))
            conn.commit()

        bot.send_message(user_id, f'Пользователь (@{user_who_clicked_button}) решил ваш запрос #{ticket_id}')
        bot.delete_message(call.message.chat.id, call.message.message_id)
        cleanup_media_files(ticket_id)
    else:
        logging.error(f'Error in handle_respond_button: user_id not found for ticket_id {ticket_id}')

"""Получаем id юзера из чата который изменил статус тикета и отправляем юзеру который создал тикет."""
def process_respond(call, ticket_id, user_who_clicked_button):
    user_id = call.message.chat.id
    supp = user_who_clicked_button
    bot.answer_callback_query(callback_query_id=call.id, text='Статус заявки изменен на "Завершен"')
    try:
        bot.send_message(user_id, f'Пользователь (@{supp}) решил ваш запрос #{ticket_id}')
    except Exception as e:
        logging.error(f'Error in process_respond: {e}')



"""Запускаем бота."""
while True:
    try:
        bot.polling(none_stop=True)
    except:
        print('zap!')
        logging.error('error: {}'.format(sys.exc_info()[0]))
