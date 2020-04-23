from flask import jsonify, request, url_for, redirect
from paginate_sqlalchemy import SqlalchemyOrmPage

from data.categories import Category
from flask_restful import Resource, abort
from data.users import User
from data.messages import Message
from data import db_session
from data.utils import success, blank_query, wrong_query
from datetime import datetime


PARAMS_ARR = ['sender_id', 'recipient_id', 'body']


def id_check_user(user_id):
    """Проверка ID пользователя на валидность"""
    session = db_session.create_session()
    user = session.query(User).get(user_id)
    if not user:
        abort(404, message=f"User {user_id} not found")


def id_check_message(message_id):
    session = db_session.create_session()
    user = session.query(Message).get(message_id)
    if not user:
        abort(404, message=f"Message {message_id} not found")


class MessagesResource(Resource):
    def get(self, message_id):
        id_check_message(message_id)
        session = db_session.create_session()
        message = session.query(Message).get(message_id)
        return jsonify({'message': message.to_dict(only=('sender_id', 'recipient_id', 'body'))})


class MessagesListResource(Resource):
    def get(self):
        if not request.json:
            return blank_query()
        elif not all(key in request.json for key in ['user_id', 'password']):
            return wrong_query()
        args = request.json
        id_check_user(args['user_id'])
        page = args.get('page', 1, type=int)
        session = db_session.create_session()
        user = session.query(User).get(args['user_id'])
        if user.hashed_password != args['password']:
            return jsonify({'error': 'Операция запрещена'})
        next_url, prev_url = None, None
        messages = user.messages_received.order_by(
            Message.timestamp.desc())
        if messages:
            page_cur = SqlalchemyOrmPage(messages, page=page, items_per_page=5)
            if page <= page_cur.item_count:
                next_url = str(page + 1) \
                    if page + 1 <= page_cur.page_count else None
                prev_url = str(page - 1) \
                    if page > 1 else None
                query = page_cur.items
            else:
                return wrong_query()
        else:
            query = messages.all()
        return jsonify({'received': [message.to_dict(only=('sender_id', 'recipient_id', 'body')) for message in query],
                        'next_url': next_url,
                        'prev_url': prev_url})

    def post(self):
        try:
            if not request.json:
                return blank_query()
            elif not all(key in request.json for key in PARAMS_ARR + ['password']):
                return wrong_query()
            args = request.json
            id_check_user(args['sender_id'])
            session = db_session.create_session()
            user = session.query(User).get(args['sender_id'])
            if user.hashed_password != args['password']:
                return jsonify({'error': 'Операция запрещена'})
            message = Message(sender_id=args['sender_id'],
                              recipient_id=args['recipient_id'],
                              body=args['body'])
            session.merge(message)
            session.commit()
            return success()
        except Exception as e:
            return jsonify({'error': e.__repr__()})
