from flask import jsonify, request
from flask.views import MethodView
from flask_login import current_user
from requests import get
from sqlalchemy import or_

from data.distance import lonlat_distance
from flask_restful import reqparse, Api, Resource, abort
from data.products import Product
from data import db_session
from data.users import User
from data.utils import get_coordinates

CREATE_ARR = ['name', 'user_id', 'description', 'cost', 'photos', 'point',
              'radius', 'email', 'number']


def id_check_product(product_id):
    session = db_session.create_session()
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        abort(404, message=f"Product {product_id} not found")


def id_check_user(user_id):
    session = db_session.create_session()
    user = session.query(User).get(user_id)
    if not user:
        abort(404, message=f"User {user_id} not found")


class ProductsResource(Resource):
    def get(self, product_id):
        id_check_product(product_id)
        session = db_session.create_session()
        product = session.query(Product).get(product_id)
        return jsonify({
            'product': product.to_dict(only=('name', 'user_id', 'description', 'cost', 'is_active', 'photos',
                                             'point_longitude', 'point_latitude', 'radius', 'contact_email',
                                             'contact_number'))
        })

    def delete(self, product_id):
        id_check_product(product_id)
        session = db_session.create_session()
        product = session.query(Product).get(product_id)
        session.delete(product)
        session.commit()
        return jsonify({'success': 'OK'})

    def put(self, product_id):
        try:
            id_check_product(product_id)
            if not request.json:
                return jsonify({'error': 'Пустой запрос'})
            elif not all(key in request.json for key in CREATE_ARR + ['is_active']):
                return jsonify({'error': 'Неправильный запрос'})
            session = db_session.create_session()
            args = request.json
            product = session.query(Product).get(product_id)
            product.name = args['name']
            product.description = args['description']
            product.cost = args['cost']
            product.is_active = args['is_active']
            product.photos = args['photos']
            product.radius = args['radius']
            product.contact_email = args['email']
            product.contact_number = args['number']
            product.longitude, product.latitude = map(float, args['point'].split(' '))
            session.commit()
            return jsonify({'success': 'OK'})
        except Exception:
            return jsonify({'error': 'Неправильный запрос'})


class ProductsListResource(Resource):
    def get(self):
        session = db_session.create_session()
        products = session.query(Product).filter(Product.is_active == 1)
        if request.json:
            args = request.json
            for query in args.keys():
                if query == 'cost':
                    mi, ma = map(int, args['cost'].split(','))
                    print(mi, ma)
                    products = products.filter(mi <= Product.cost).filter(Product.cost <= ma)
                elif query == 'name':
                    products = products.filter(Product.name.like(f'%{args["name"]}%'))
                elif query == 'category':
                    products = products.filter(Product.name == args['category'])
        return jsonify({
            'product': [item.to_dict(only=('name', 'user_id', 'description', 'cost', 'is_active', 'photos',
                                           'point_longitude', 'point_latitude', 'radius', 'contact_email',
                                           'contact_number')) for item in products.all()]
        })

    def post(self):
        session = db_session.create_session()
        args = request.json
        print(args)
        print(list(key in args for key in CREATE_ARR))
        if not args:
            return jsonify({'error': 'Пустой запрос'})
        elif not all(key in args for key in CREATE_ARR):
            return jsonify({'error': 'Неправильный запрос'})
        point_longitude, point_latitude = map(float, args['point'].split())
        product = Product(
            name=args['name'],
            user_id=args['user_id'],
            description=args['description'],
            cost=args['cost'],
            is_active=True,
            photos=args['photos'],
            point_longitude=point_longitude,
            point_latitude=point_latitude,
            radius=args['radius'],
            contact_number=args['number'],
            contact_email=args['email']
        )
        session.add(product)
        session.commit()
        return jsonify({'success': 'OK'})
