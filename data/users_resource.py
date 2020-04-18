from flask import jsonify, request
from flask_restful import reqparse, Api, Resource, abort
from data.users import User
from data import db_session
from data.utils import success, wrong_query, blank_query

REGISTER_ARR = ['name', 'surname', 'hometown', 'mobile_telephone', 'address', 'email', 'password']
LOGIN_ARR = ['email', 'password']


def id_check(user_id):
    session = db_session.create_session()
    user = session.query(User).get(user_id)
    if not user:
        abort(404, message=f"User {user_id} not found")


class UsersResource(Resource):
    def get(self, user_id):
        id_check(user_id)
        session = db_session.create_session()
        user = session.query(User).get(user_id)
        return jsonify({
            'user': user.to_dict(only=('name', 'surname', 'hometown', 'mobile_telephone', 'deals_number', 'rating',
                                       'photo_id', 'address', 'email'))
        })

    def delete(self, user_id):
        id_check(user_id)
        session = db_session.create_session()
        user = session.query(User).get(user_id)
        session.delete(user)
        session.commit()
        return success()

    def put(self, user_id):
        try:
            id_check(user_id)
            if not request.json:
                return blank_query()
            elif not all(key in request.json for key in REGISTER_ARR):
                return wrong_query()
            session = db_session.create_session()
            user = session.query(User).get(User.id).first()
            args = request.json
            user.name = args['name']
            user.surname = args['surname']
            user.hometown = args['hometown']
            user.email = args['email']
            user.address = args['address']
            user.mobile_telephone = args['mobile_telephone']
            user.set_password(args['password'])
            user.photo_id = args['photo_id']
            session.commit()
            return success()
        except Exception:
            return wrong_query()


class UsersListResource(Resource):
    def get(self):
        session = db_session.create_session()
        users = session.query(User).all()
        return jsonify({
            'user': [item.to_dict(only=('name', 'surname', 'hometown', 'mobile_telephone', 'deals_number', 'rating',
                                        'photo_id', 'address', 'email')) for item in users]
        })

    def post(self):
        session = db_session.create_session()
        args = request.json
        print(args)
        print(list(key in args for key in REGISTER_ARR))
        if not args:
            return blank_query()
        elif not all(key in args for key in REGISTER_ARR):
            return wrong_query()
        if session.query(User).filter(User.email == args['email']).first():
            return jsonify({'error': 'Пользователь с таким email уже существует'})
        if session.query(User).filter(User.mobile_telephone == args['mobile_telephone']).first():
            return jsonify({'error': 'Пользователь с таким номером телефона уже существует'})
        user = User(
            name=args['name'],
            surname=args['surname'],
            mobile_telephone=args['mobile_telephone'],
            hometown=args['hometown'],
            address=args['address'],
            email=args['email'],
            deals_number=0,
            rating=0,
            photo_id=args['photo_id']
        )
        user.set_password(args['password'])
        session.add(user)
        session.commit()
        return success()
    
    def put(self):
        try:
            session = db_session.create_session()
            args = request.json
            if not args:
                return blank_query()
            elif not all(key in args for key in LOGIN_ARR):
                return wrong_query()
            user = session.query(User).filter(User.email == args['email']).first()
            if not user:
                return jsonify({'error': 'Пользователя с таким email не существует'})
            if not user.check_password(args['password']):
                return jsonify({'error': 'Неверный пароль'})
            return jsonify({'success': 'OK', 'user_id': user.id})
        except Exception as e:
            print(e)
            return wrong_query()
