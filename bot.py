import io
import os
from PIL import Image

from data import db_session
from data.categories import Category
import requests

from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from config import TOKEN
from data.photos import Photo
from data.users import User


class Bot:
    """Бот для взаимодействия с сайтом"""
    def __init__(self):
        """Инициализация"""
        self.authorization_status = False
        self.login_status = False

        self.buy = False

        self.session = db_session.create_session()
        self.all_users = requests.get(f'http://localhost:5000/api/users').json()['user']
        self.categories = requests.get(f'http://localhost:5000/api/products').json()['product']
        self.categories_index = {}
        for i in self.session.query(Category).all():
            self.categories_index[i.id] = i.category
        self.products = {}
        for i in self.categories:
            if not self.categories_index[i['category']] in self.products.keys():
                self.products[self.categories_index[i['category']]] = [i]
            elif self.categories_index[i['category']] in self.products.keys():
                self.products[self.categories_index[i['category']]].append(i)
        for photo in self.session.query(Photo):
            Image.open(io.BufferedReader(io.BytesIO(photo.photo))).convert('RGB').save(f'photos/{photo.id}.jpg')

        self.user = None
        self.category = None
        self.product = None

        self.button_log_in = 'Авторизоваться'
        self.button_register = 'Зарегистрироваться'
        self.button_start = '/start'
        self.button_logout = '/logout'

        self.menu_button_0 = 'Купить'
        self.menu_button_1 = 'Аккаунт'

        self.category_button_0 = 'Транспорт'
        self.category_button_1 = 'Недвижимость'
        self.category_button_2 = 'Работа'
        self.category_button_3 = 'Услуги'
        self.category_button_4 = 'Личные вещи'
        self.category_button_5 = 'Для дома и дачи'
        self.category_button_6 = 'Бытовая электроника'
        self.category_button_7 = 'Хобби и отдых'
        self.category_button_8 = 'Животные'
        self.category_button_9 = 'Для бизнеса'

        self.request_kward = {'proxy_url': 'socks5://127.0.0.1:9150'}

    def first_keyboard(self):
        """Клавиатура стартового меню авторизации"""
        keyboard = [
            [
                KeyboardButton(self.button_log_in),
                KeyboardButton(self.button_register)
            ]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    def start_keyboard(self):
        """Клавиатура возвращения меню авторизации"""
        keyboard = [
            [
                KeyboardButton(self.button_start)
            ]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    def start_logout_keyboard(self):
        """Клавиатура для выхода из аккаунта и возвращения в меню магазина"""
        keyboard = [
            [
                KeyboardButton(self.button_start),
                KeyboardButton(self.button_logout)
            ]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    def categories_keyboard(self):
        """Клавиатура с категориями"""
        keyboard = [
            [
                KeyboardButton(self.category_button_0),
                KeyboardButton(self.category_button_2),
                KeyboardButton(self.category_button_3),
                KeyboardButton(self.category_button_8)
            ],
            [
                KeyboardButton(self.category_button_1),
                KeyboardButton(self.category_button_4),
                KeyboardButton(self.category_button_9)
            ],
            [
                KeyboardButton(self.category_button_5),
                KeyboardButton(self.category_button_6),
                KeyboardButton(self.category_button_7)
            ],
            [
                KeyboardButton(self.button_start),
                KeyboardButton(self.button_logout)
            ]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    def menu_keyboard(self):
        """Клавиатура стартового меню магазина"""
        keyboard = [
            [
                KeyboardButton(self.menu_button_0),
                KeyboardButton(self.menu_button_1)
            ],
            [
                KeyboardButton(self.button_start),
                KeyboardButton(self.button_logout)
            ]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    def checker(self, email, status=None):
        """Проверка e-mail на валидность"""
        if status == 'Mail':
            try:
                login, domen = email.split('@')
            except Exception:
                return False
            return True

    def errors(self, update, context, status=None):
        """Возвращает ошибку в зависимости от контекста"""
        if status == 'Mail':
            update.message.reply_text('Некорректно введена почта.\nПопробуйте ввести снова.',
                                      reply_markup=ReplyKeyboardRemove())
            return self.login_request(update, context)
        elif status == 'Password':
            update.message.reply_text('Неправильно введен пароль.\nПопробуйте ввести снова.',
                                      reply_markup=ReplyKeyboardRemove())
            return self.login_request(update, context)
        elif status == 'User not found':
            update.message.reply_text('Такого пользователя не существует.\nПопробуйте ввести снова.',
                                      reply_markup=ReplyKeyboardRemove())
            return self.login_request(update, context)
        elif status == 'Wrong input':
            update.message.reply_text('Вы неправильно ввели данные.\nПопробуйте ввести снова.',
                                      reply_markup=ReplyKeyboardRemove())
            return self.login_request(update, context)
        elif status == 'Menu not found':
            update.message.reply_text('Такой функции в меню не существует.\nПопробуйте ввести снова.',
                                      reply_markup=self.menu_keyboard())
        elif status == 'Category not found':
            update.message.reply_text('Такой категории не существует.\nПопробуйте ввести снова.',
                                      reply_markup=self.categories_keyboard())
        elif status == 'Product not found':
            update.message.reply_text('Такого продукта нет в списке.\nПопробуйте ввести ID продукта снова.',
                                      reply_markup=self.start_logout_keyboard())

    def logout(self, update, context):
        """Процедура выхода из аккаунта"""
        if self.authorization_status:
            self.authorization_status = False
            self.category = None
            self.product = None
            self.buy = False
            update.message.reply_text(f'Пользователь {self.user["name"].title()} вышел из аккаунта!',
                                      reply_markup=self.start_keyboard())
            self.user = None
            return self.authorization(update, context)
        else:
            update.message.reply_text('Вы не авторизовались!',
                                      reply_markup=ReplyKeyboardRemove())
            return self.authorization(update, context)

    def authorization(self, update, context):
        """Авторизация"""
        if not self.authorization_status:
            self.login_status = False
            update.message.reply_text('Добрый день! Для входа в магазин вам нужно авторизоваться.',
                                      reply_markup=self.first_keyboard())
        elif self.authorization_status:
            self.product = None
            self.category = None
            self.buy = False
            return self.success_authorization(update, context)

    def login_request(self, update, context):
        """Запрос на данные для логина"""
        update.message.reply_text('Введите email и пароль через пробел.',
                                  reply_markup=self.start_keyboard())
        self.login_status = True

    def register(self, update, context):
        """Регистрация"""
        update.message.reply_text('Для того, чтобы зарегистрироваться, перейдите по ссылке.\n'
                                  'http://yandexlyceum-shop.heroku.com/register\n'
                                  'Чтобы вернуться в меню авторизации, воспользуйтесь кнопкой /start',
                                  reply_markup=self.start_keyboard())

    def success_authorization(self, update, context):
        """Главное меню (доступное после авторизации)"""
        update.message.reply_text(f'{self.user["name"].title()}, добро пожаловать в магазин!\n'
                                  f'Выберите дальнейшие действия.\n'
                                  f'Если вы хотите выйти из аккаунта, воспользуйтесь кнопкой /logout\n'
                                  f'Чтобы вернуться в меню магазина, воспользуйтесь кнопкой /start',
                                  reply_markup=self.menu_keyboard())

    def select_category(self, update, context):
        """Меню 'Выбрать категорию'"""
        update.message.reply_text('Чтобы совершить покупку, вам необходимо выбрать категорию.',
                                  reply_markup=self.categories_keyboard())

    def selected_category(self, update, context):
        """Показ товаров заданной категории"""
        update.message.reply_text(f'{self.user["name"].title()}, вы выбрали категорию {self.category}.\n'
                                  f'Сейчас мы предоставим вам список товаров.\n'
                                  f'Для того, чтобы купить товар, выберите его ID.',
                                  reply_markup=self.start_logout_keyboard())
        for i in self.products[self.category]:
            self.select_product(update, context, i)

    def seller_name(self, user_id):
        """Возвращает имя продавца"""
        for i in self.all_users:
            if i["email"] == user_id:
                return i["name"]
        return 'не указано'

    def select_product(self, update, context, i):
        """Процедура вывода объявлений на экран"""
        info = ''
        info += f'ID товара: {i["id"]}\n'
        info += f'Наименование товара: {i["name"]}\n'
        info += f'Цена: {i["cost"]} руб.\n'
        if i["description"]:
            info += f'Описание: {i["description"]}\n'
        else:
            info += f'Описание: нет описания\n'
        info += f'Имя продавца: {self.seller_name(i["contact_email"])}\n'
        info += f'Контактный номер: {i["contact_number"]}'
        update.message.reply_text(info,
                                  reply_markup=self.start_logout_keyboard())
        return self.send_photo(update, context, status='Product', i=i["photos"])

    def send_photo(self, update, context, status=None, i=None):
        """Процедура отправки фото"""
        if status == 'Account':
            if self.user["photo_id"]:
                try:
                    file = open(f'photos/{self.user["photo_id"] - 1}.jpg', 'rb')
                except Exception:
                    file = open(f'photos/{self.user["photo_id"] - 1}.png', 'rb')
            else:
                try:
                    file = open(f'photos/0.jpg', 'rb')
                except Exception:
                    file = open(f'photos/0.png', 'rb')
            context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo=file
            )
        elif status == 'Product':
            try:
                file = open(f'photos/{int(i) - 1}.jpg', 'rb')
            except Exception:
                file = open(f'photos/{int(i) - 1}.png', 'rb')
            context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo=file
            )

    def account(self, update, context):
        """Экран с данными о пользователе"""
        update.message.reply_text(f'Данные пользователя:\n'
                                  f'Фамилия: {self.user["surname"]}\n'
                                  f'Имя: {self.user["name"]}\n'    
                                  f'Адрес: {self.user["address"]}\n'
                                  f'Контактный номер: {self.user["mobile_telephone"]}\n',
                                  reply_markup=self.menu_keyboard())
        return self.send_photo(update, context, status='Account')

    def selected_product(self, update, context):
        """Процедура обработки выбранного товара"""
        update.message.reply_text(f'Вы выбрали товар {self.product["name"]}!\n'
                                  f'Мы скоро уведомим продавца о том, что вы хотите купить товар.\n'
                                  f'Также вы можете сами связаться с ним по телефону.',
                                  reply_markup=self.start_logout_keyboard())
        return self.success_buy(update, context)

    def success_buy(self, update, context):
        """Процедура вывода благодарности при покупке"""
        update.message.reply_text('Спасибо за покупку!',
                                  reply_markup=self.start_logout_keyboard())

    def echo(self, update, context):
        """Ядро"""
        message = update.message.text

        if self.login_status:
            try:
                email, password = message.split()
            except Exception:
                return self.errors(update, context, status='Wrong input')
            if self.checker(email, status='Mail'):
                for user in self.session.query(User).all():
                    if user.email == email and user.check_password(password):
                        self.login_status = False
                        self.authorization_status = True
                        for i in self.all_users:
                            if user.email == i["email"]:
                                self.user = i
                        return self.success_authorization(update, context)
                    elif user.email == email and not user.check_password(password):
                        return self.errors(update, context, status='Password')
                return self.errors(update, context, status='User not found')
            else:
                return self.errors(update, context, status='Mail')

        if self.authorization_status and not all([self.buy]):
            if message in [self.menu_button_0, self.menu_button_1]:
                if message == self.menu_button_0:
                    self.buy = True
                    return self.select_category(update, context)
                elif message == self.menu_button_1:
                    return self.account(update, context)
            else:
                return self.errors(update, context, status='Menu not found')
        if self.authorization_status:
            if self.buy:
                if self.category is None:
                    if message in self.products.keys():
                        self.category = message
                        return self.selected_category(update, context)
                    else:
                        return self.errors(update, context, status='Category not found')
                elif self.category:
                    print(1)
                    if self.product is None:
                        print(self.products)
                        print(self.category)
                        print(self.products[self.category])
                        if message in [str(i["id"]) for i in self.products[self.category]]:
                            for i in self.products[self.category]:
                                if str(i["id"]) == message:
                                    self.product = i
                            return self.selected_product(update, context)
                        else:
                            return self.errors(update, context, status='Product not found')

        if message == self.button_register:
            return self.register(update, context)
        elif message == self.button_log_in:
            return self.login_request(update, context)
        else:
            return self.authorization(update, context)

    def main(self):
        """Создание бота"""
        updater = Updater(token=TOKEN, use_context=True, request_kwargs=self.request_kward)
        dispatcher = updater.dispatcher

        start_handler = CommandHandler('start', self.authorization)
        updater.dispatcher.add_handler(start_handler)
        logout_handler = CommandHandler('logout', self.logout)
        updater.dispatcher.add_handler(logout_handler)

        message_handler = MessageHandler(Filters.text, self.echo)
        updater.dispatcher.add_handler(message_handler)

        updater.start_polling()
        updater.idle()


if __name__ == '__main__':
    #  запуск нужных для работы утилит
    db_session.global_init(os.path.join('db', 'shop.sqlite'))
    Bot().main()