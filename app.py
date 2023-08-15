from flask import Flask, request
import csv
import telebot
import time
import random
from dotenv import load_dotenv
import os


load_dotenv('.env')
#app = Flask(__name__)


# Ініціалізація токену
bot_token = os.environ.get('bot_token', '')
bot = telebot.TeleBot(bot_token)


# Словник з цінами по районах
prices_per_district = {
    "Орджонікідзевський": 100,
    "Дзержинський": 150,
    "Червонозаводський": 120,
    "Київський": 130,
    "Жовтневий": 140,
    "Фрунзенський": 160,
    "Московський": 170,
    "Комінтернівський": 180,
    "Ленінський": 190
}


@bot.message_handler(commands=['start'])
def start(message):
    """
    Start command handler. 

    Args:
        message (string): displays a welcome message.
    """
    
    bot.send_message(message.chat.id, "Привіт! На якій вулиці ви знаходитесь?")
    bot.register_next_step_handler(message, handle_street_from)


def handle_street_from(message):
    """ 
    Processes the street name, stores it and asks for the house number.

    Args:
        message (string): a message from a user with a street name.
    """
    street_from = message.text
    bot.send_message(message.chat.id, f"Введіть номер будинку '{street_from}':")
    bot.register_next_step_handler(message, handle_house_number_from, street_from)


def handle_house_number_from(message, street_from):
    """ 
    Processes the house number sent by the user in the previous step.
    Asks for the name of the street where the user plans to go.

    Args:
        message (string): a message from a user with a house number.
        street_from (string): the street name from the previous step
    """
    
    house_number_from = message.text
    bot.send_message(message.chat.id, "Привіт! Введи назву вулиці куди ви їдете:")
    bot.register_next_step_handler(message, handle_street, street_from, house_number_from)


def handle_street(message, street_from, house_number_from):
    """
    Processes the name of the street where the user plans to go.
    Checks whether such a street exists in the database.

    Args:
        message (string): a message from a user with a street name.
        street_from (string): the street name from the previous step
        house_number_from (integer): the number of the house from which the user plans to leave.
    """
    
    street = message.text

    try:
        bot.send_message(message.chat.id, f"Введіть номер будинку '{street}':")
        bot.register_next_step_handler(message, handle_house_number, street_from, house_number_from, street)
    except Exception as e:
        bot.send_message(message.chat.id, f"Під час обробки виникла помилка: {str(e)}")


def handle_house_number(message, street_from, house_number_from, street):
    """
    Processes the number of the house where the user plans to go.
    Search and output information about the trip and price by district.

    Args:
        message (integer): a message from a user with a house number.
        street_from (string): the street name from the previous step.
        house_number_from (integer): The number of the house from which the user plans to leave.
        street (string): the name of the street where the user plans to go.
    """
    
    house_number = message.text

    try:
        with open('adress.csv', 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            next(csv_reader)
            for row in csv_reader:
                district, street_type, street_name = row
                if street.lower() == street_name.lower():
                    bot.send_message(message.chat.id, f"Ви виїджаєте з {street_from} {house_number_from} до {street_name} {house_number} в район {district}.")

                    base_price = prices_per_district.get(district, 0)
                    bot.send_message(message.chat.id, f"Ціна поїздки на стандартному авто: {base_price:.2f} грн")
                    bot.send_message(message.chat.id, f"Ціна поїздки на комфортному авто: {base_price * 1.2:.2f} грн")
                    bot.send_message(message.chat.id, f"Ціна поїздки на бізнес-класі: {base_price * 1.4:.2f} грн")

                    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                    keyboard.add(*[telebot.types.KeyboardButton(car_type) for car_type in ["стандарт", "комфорт", "бізнес"]])
                    bot.send_message(message.chat.id, "Обери тип авто:", reply_markup=keyboard)
                    bot.register_next_step_handler(message, handle_car_type, district)
                    return
    
        bot.send_message(message.chat.id, "Вулиця не знайдена. Спробуйте ще раз:")
    except Exception as e:
        bot.send_message(message.chat.id, f"Під час обробки виникла помилка: {str(e)}")


def handle_car_type(message, district):
    """
    Processes the car category selected by the user and displays the price of the trip.

    Args:
        message (string): Message from the user with the selected car category.
        district (string): the district where the trip takes place.
    """
    
    car_type = message.text.lower()
    price_multiplier = 1.0

    if car_type == "комфорт":
        price_multiplier = 1.2
    elif car_type == "бізнес":
        price_multiplier = 1.4

    base_price = prices_per_district.get(district, 0)
    price = base_price * price_multiplier
    bot.send_message(message.chat.id, f"Ціна поїздки на {car_type} авто: {price:.2f} грн")

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    confirm_button = telebot.types.KeyboardButton("Підтверджую")
    back_button = telebot.types.KeyboardButton("Назад")
    keyboard.add(confirm_button, back_button)
    bot.send_message(message.chat.id, "Підтверджуєте замовлення?", reply_markup=keyboard)
    bot.register_next_step_handler(message, handle_confirmation, district, car_type, price)


def handle_confirmation(message, district, car_type, price):
    """
    Processes user confirmation of car selection and finds available drivers.

    Args:
        message (string): message from the user confirming the order.
        district (string): the area where the trip takes place.
        car_type (string): selected car category.
        price (float): the price of the trip.
    """
    
    choice = message.text.lower()
    if choice == "підтверджую":
        try:
            with open('drivers.csv', 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                next(csv_reader)  # Пропускаємо перший рядок
                drivers = list(csv_reader)
                if drivers:
                    selected_driver = random.choice(drivers)
                    color, company, model, driver_id = selected_driver

                    bot.send_message(message.chat.id, "Шукаю водія...")
                    time.sleep(2)  # Затримка на 2 секунди

                    bot.send_message(message.chat.id, f"Водій вже до вас прямує. {color} {company} {model}. {driver_id}")
                else:
                    bot.send_message(message.chat.id, "Наразі немає доступних водіїв.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Під час обробки виникла помилка: {str(e)}")
    elif choice == "назад":
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*[telebot.types.KeyboardButton(car_type) for car_type in ["стандарт", "комфорт", "бізнес"]])
        bot.send_message(message.chat.id, "Обери тип авто:", reply_markup=keyboard)
        bot.register_next_step_handler(message, handle_car_type, district)
    else:
        bot.send_message(message.chat.id, "Незрозумілий вибір. Будь ласка, оберіть 'Підтверджую' або 'Назад'.")


#@app.route('/' + bot_token, methods=['POST'])
#def get_message():
#    json_string = request.get_data().decode('utf-8')
#    update = telebot.types.Update.de_json(json_string)
#    bot.process_new_updates([update])
#    return 'Test Bot', 200


#@app.route('/')
#def webhook():
#    bot.remove_webhook()
#    bot.set_webhook(url='http://test-bot-cicd-knu.herokuapp.com/' + bot_token)
#    return 'Test Bot', 200

if __name__ == "__main__":
#    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    bot.polling()