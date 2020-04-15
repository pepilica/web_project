from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler
from config import TOKEN
from data.users import User
from data import db_session

session = db_session.create_session()
users = session.query(User).first()
for user in users:
    print(user)

REQUEST_KWARGS = {
                'proxy_url': 'socks5://127.0.0.1:9150',
                # Адрес прокси сервера
                # Опционально, если требуется аутентификация:
                # 'urllib3_proxy_kwargs': {
                #     'assert_hostname': 'False',
                #     'cert_reqs': 'CERT_NONE',
                #     'username': 'user',
                #     'password': 'password'
                #     }
                }



def authorization(update, context):
    update.message.reply_text('Оле')


def main():
    updater = Updater(token=TOKEN, request_kwargs=REQUEST_KWARGS, use_context=True)
    dispatcher = updater.dispatcher
    text_handler = MessageHandler(Filters.text, authorization)
    dispatcher.add_handler(text_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()