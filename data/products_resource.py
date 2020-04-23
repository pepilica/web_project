from flask import jsonify, request, url_for
from data.categories import Category
from flask_restful import Resource, abort
from data.products import Product
from data import db_session
from data.users import User
from data.utils import success, blank_query, wrong_query
from datetime import datetime

CREATE_ARR = ['name', 'user_id', 'description', 'cost', 'photos', 'point',
              'radius', 'email', 'number', 'category']


def id_check_product(product_id):
    """Проверка ID продукта на валидность"""
    session = db_session.create_session()
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        abort(404, message=f"Product {product_id} not found")


def id_check_user(user_id):
    """Проверка ID пользователя на валидность"""
    session = db_session.create_session()
    user = session.query(User).get(user_id)
    if not user:
        abort(404, message=f"User {user_id} not found")


class ProductsResource(Resource):
    """Работа с продуктом"""
    def get(self, product_id):
        """Получение данных о продукте"""
        id_check_product(product_id)
        session = db_session.create_session()
        product = session.query(Product).get(product_id)
        return jsonify({
            'product': product.to_dict(only=('id', 'name', 'user_id', 'description', 'cost', 'is_active', 'photos',
                                             'point_longitude', 'point_latitude', 'radius', 'contact_email',
                                             'contact_number', 'category'))
        })

    def delete(self, product_id):
        """Удаление продукта"""
        id_check_product(product_id)
        session = db_session.create_session()
        product = session.query(Product).get(product_id)
        session.delete(product)
        session.commit()
        return success()

    def put(self, product_id):
        """Изменение продукта"""
        try:
            id_check_product(product_id)
            if not request.json:
                return blank_query()
            elif not all(key in request.json for key in CREATE_ARR + ['is_active']):
                return wrong_query()
            session = db_session.create_session()
            args = request.json
            product = session.query(Product).get(product_id)
            product.user_id = args['user_id']
            product.name = args['name']
            product.description = args['description']
            product.photos = str(args['photos'])
            product.cost = args['cost']
            product.is_active = args['is_active']
            product.radius = args['radius']
            product.category = args['category']
            product.contact_email = args['email']
            product.contact_number = args['number']
            product.longitude, product.latitude = map(float, args['point'].split(' '))
            session.merge(product)
            session.commit()
            return success()
        except Exception as e:
            return jsonify({'error': e.__repr__()})


class ProductsListResource(Resource):
    """Работа со списком продуктов"""
    def get(self):
        """Получение списка продуктов с учетом фильтров"""
        session = db_session.create_session()
        products = session.query(Product)
        next_url, prev_url = None, None
        if request.json:
            args = request.json
            for query in args.keys():
                if query == 'cost_min':
                    mi = float(args['cost_min'])
                    products = products.filter(mi <= Product.cost)
                elif query == 'cost_max':
                    ma = float(args['cost_max'])
                    products = products.filter(Product.cost <= ma)
                elif query == 'name':
                    products = products.filter(Product.name.like(f'%{args["name"]}%'))
                elif query == 'category':
                    products = products.filter(Product.category == args['category'])
                elif query == 'user':
                    products = products.filter(Product.user_id == args['user_id'])
            products = products.filter(Product.is_active == args.get('is_active', True))
            if 'sort_by' in args.keys():
                if args['sort_by'] == 'date':
                    products = products.order_by(Product.date.desc())
                else:
                    return wrong_query()
            if args.get('paginate') in args.keys():
                if 'posts_per_page' in args.keys():
                    products = products.paginate(args.get('page', 1), args['post_per_page'], False)
                    next_url = url_for('/api/products', page=products.next_num) \
                        if products.has_next else None
                    prev_url = url_for('/api/products', page=products.prev_num) \
                        if products.has_prev else None
                    products = products.items
                else:
                    return wrong_query()
        else:
            products = products.filter(Product.is_active == True)
        products = products.all()
        return jsonify({
            'product': [item.to_dict(only=('id', 'name', 'user_id', 'description', 'cost', 'is_active', 'photos',
                                           'point_longitude', 'point_latitude', 'radius', 'contact_email',
                                           'contact_number', 'category', 'date')) for item in products],
            'next_url': next_url,
            'prev_url': prev_url
        })

    def post(self):
        """Создание продукта"""
        session = db_session.create_session()
        args = request.json
        print(args)
        print(list(key in args for key in CREATE_ARR))
        if not args:
            return blank_query()
        elif not all(key in args for key in CREATE_ARR):
            return wrong_query()
        point_longitude, point_latitude = map(float, args['point'].split(' '))
        product = Product(
            name=str(args['name']),
            user_id=args['user_id'],
            description=args['description'],
            cost=args['cost'],
            is_active=True,
            photos=str(args['photos']),
            point_longitude=point_longitude,
            point_latitude=point_latitude,
            radius=args['radius'],
            contact_number=args['number'],
            contact_email=args['email'],
            category=session.query(Category).filter(Category.identifier == args['category']).first().id if session.query(Category).filter(Category.identifier == args['category']).first() else None,
            date=datetime.now()
        )
        session.add(product)
        session.commit()
        return success()
