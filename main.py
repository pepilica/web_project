import flask_moment
import base64
import io
import os
from datetime import datetime
from paginate_sqlalchemy import SqlalchemyOrmPage
from PIL import Image
from flask import Flask, render_template, redirect, jsonify, request, flash
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
from flask_restful import Api, abort
from flask_wtf import FlaskForm
from requests import post, put, get, delete
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FileField, TextAreaField, IntegerField, \
    RadioField, MultipleFileField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from data.categories import Category
from data import db_session
from data.messages import Message
from data.notifications import Notification
from data.photos_resource import PhotosListResource, PhotosResource
from data.products import Product
from data.products_resource import ProductsResource, ProductsListResource
from data.users import User
from data.users_resource import UsersListResource, UsersResource
from data.utils import check_photo, get_coordinates, get_city, get_address
from data.constants import CATEGORIES, POSTS_PER_PAGE, SORT_BY

port = int(os.environ.get("PORT", 5000))  # подключение к необходимому порту
app = Flask(__name__)  # здесь и далее инициализация приложения
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['SQLALCHEMY_ECHO'] = True
login_manager = LoginManager()
login_manager.init_app(app)
user_api = Api(app)
moment = flask_moment.Moment(app)
user_api.add_resource(UsersResource, '/api/users/<int:user_id>')
user_api.add_resource(UsersListResource, '/api/users')
user_api.add_resource(PhotosResource, '/api/photos/<int:photo_id>')
user_api.add_resource(PhotosListResource, '/api/photos')
user_api.add_resource(ProductsResource, '/api/products/<int:product_id>')
user_api.add_resource(ProductsListResource, '/api/products')


#  Формы для приложения

class ConfirmForm(FlaskForm):
    confirm = BooleanField("Да, я согласен", validators=[DataRequired()])
    submit = SubmitField('Удалить')


class ProductFilterForm(FlaskForm):
    name = StringField('Поиск по названию', validators=[Length(max=128, message='Неверно введено название'),
                                                        Optional()])
    cost_min = IntegerField('Минимальная цена', validators=[NumberRange(min=0, message='Неверная минимальная цена'),
                                                            Optional()])
    cost_max = IntegerField('Максимальная цена', validators=[NumberRange(min=0, message='Неверная максимальная цена'),
                                                             Optional()])
    category = RadioField('Категория', choices=[(CATEGORIES[i], i) for i in CATEGORIES.keys()] +
                                               [('no', 'Без категории')], validators=[Optional()])
    submit = SubmitField('Показать!')


class RegisterForm(FlaskForm):
    surname = StringField('Фамилия', validators=[DataRequired()])
    name = StringField('Имя', validators=[DataRequired()])
    email = EmailField('E-mail', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    hometown = StringField('Город проживания', validators=[DataRequired()])
    address = StringField('Адрес', validators=[DataRequired()])
    phone = StringField('Мобильный телефон', validators=[DataRequired()])
    photo = FileField('Фотография профиля(не менее 200x200, не более 2000x2000). Форматы: jpg, png.')
    submit = SubmitField('Зарегистрироваться!')


class LoginForm(FlaskForm):
    email = EmailField('E-mail', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти!')


class MessageForm(FlaskForm):
    message = TextAreaField('Message', validators=[
        DataRequired(), Length(min=0, max=140)])
    submit = SubmitField('Submit')


class EditForm(FlaskForm):
    surname = StringField('Фамилия', validators=[DataRequired()])
    name = StringField('Имя', validators=[DataRequired()])
    hometown = StringField('Город проживания', validators=[DataRequired()])
    address = StringField('Адрес', validators=[DataRequired()])
    phone = StringField('Мобильный телефон', validators=[DataRequired()])
    submit = SubmitField('Изменить')


class ProductForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание (не больше 2000 символов)', validators=[Length(max=2000)])
    cost = IntegerField('Стоимость (в рублях)', validators=[DataRequired()])
    photos = MultipleFileField('Выберите фотографии (не более 10)', validators=[Length(max=10), Optional()])
    radius = IntegerField('Радиус поиска (в метрах, не более 500 км)', validators=[NumberRange(max=5 * 10 ** 5),
                                                                                   Optional()])
    actual_address = BooleanField('Показывать фактический адрес', validators=[Optional()])
    geopoint = StringField('Адрес',  validators=[DataRequired()])
    category = RadioField('Категория', choices=[(CATEGORIES[i], i) for i in CATEGORIES.keys()] +
                                               [('no', 'Без категории')], validators=[Optional()])
    phone = StringField('Контактный телефон', validators=[Optional()])
    email = EmailField('Контактный электронный адрес', validators=[Optional()])
    submit = SubmitField('Добавить!')


@login_manager.user_loader
def load_user(user_id):
    """Загрузчик пользователя"""
    session = db_session.create_session()
    return session.query(User).get(user_id)


@app.route('/register', methods=['POST', 'GET'])
def register():
    """Регистрация"""
    if current_user.is_authenticated:
        return redirect('/')
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не сходятся", current_user=current_user, args=None)
        print(form.photo.data)
        print(form.photo.data.content_type)
        if not form.photo.data.filename:
            photo_output = 1
        else:
            if form.photo.data.content_type in ('image/png', 'image/jpeg'):
                photo = io.BytesIO(form.photo.data.read())
                photograph = Image.open(photo)
                if not check_photo(photograph):
                    return render_template('register.html', title='Регистрация',
                                           form=form,
                                           message='Фотография не подходит по размеру', current_user=current_user,
                                           args=None)
                photograph.save(photo, format='PNG')
                response_photo = post(f'http://0.0.0.0:{port}/api/photos', json={
                    'photo': base64.b64encode(photo.getvalue()).decode()
                }).json()
                photo_output = response_photo['photo_id']
                if 'success' not in response_photo.keys():
                    return render_template('register.html', title='Регистрация',
                                           form=form,
                                           message=response_photo['error'], current_user=current_user, args=None)
            else:
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message='Неверный формат файла', current_user=current_user, args=None)
        response = post(f'http://0.0.0.0:{port}/api/users', json={
            'name': form.name.data,
            'surname': form.surname.data,
            'hometown': get_city(form.hometown.data),
            'mobile_telephone': form.phone.data,
            'address': form.address.data,
            'email': form.email.data,
            'password': form.password.data,
            'photo_id': photo_output
        }).json()
        print(response)
        if 'success' in response.keys():
            return redirect('/')
        else:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message=response['error'], current_user=current_user, args=None)
    return render_template('register.html', title='Регистрация', form=form, current_user=current_user, args=None)


@app.route('/login', methods=['POST', 'GET'])
def login():
    """Логин"""
    if current_user.is_authenticated:
        print(0)
        return redirect('/')
    form = LoginForm()
    if form.validate_on_submit():
        response = put(f'http://0.0.0.0:{port}/api/users', json={
            'email': form.email.data,
            'password': form.password.data
        }).json()
        print(response)
        if 'success' in response.keys():
            session = db_session.create_session()
            user = session.query(User).get(response['user_id'])
            print(form.remember_me.data)
            login_user(user, remember=form.remember_me.data)
            return redirect('/')
        else:
            return render_template('login.html', title='Вход',
                                   form=form,
                                   message=response['error'], current_user=current_user, args=None)
    return render_template('login.html', title='Вход',
                           form=form, current_user=current_user, args=None)


@app.route('/')
@app.route('/index')
def main():
    """Титульная страница"""
    return render_template('index.html', title='Магазин', current_user=current_user, args=None,
                           session=db_session.create_session(), Category=Category)


@app.route('/logout')
@login_required
def logout():
    """Выход из аккаунта"""
    logout_user()
    return redirect("/")


@app.route('/products', methods=['POST', 'GET'])
def products_main():
    """Показ товаров"""
    form = ProductFilterForm()
    page = request.args.get('page', 1, type=int)
    sort_by = SORT_BY
    posts_per_page = POSTS_PER_PAGE
    json_file = {
        'paginate': True,
        'sort_by': sort_by,
        'posts_per_page': posts_per_page,
        'page': page
    }
    if form.validate_on_submit():
        if form.name.data:
            json_file['name'] = form.name.data
        if form.cost_min.data:
            json_file['cost_min'] = form.cost_min.data
        if form.cost_max.data:
            json_file['cost_max'] = form.cost_max.data
        if form.category.data:
            session = db_session.create_session()
            category = session.query(Category).filter(Category.identifier == form.category.data).first()
            if category:
                json_file['category'] = category.id
    response = get(f'http://0.0.0.0:{port}/api/products', json=json_file).json()
    if 'product' in response.keys():
        form.name.data = json_file.get('name', '')
        form.cost_min.data = json_file.get('cost_min', None)
        form.cost_max.data = json_file.get('cost_max', '')
        form.category.data = json_file.get('category', None)
        return render_template('products.html', products=response['product'], next_url=response['next_url'],
                               prev_url=response['prev_url'], session=db_session.create_session(),
                               length=len(response['product']), User=User, Category=Category, int=int, form=form,
                               get_city=get_city, args=None, title='Товары')
    return redirect('/products')


@app.route('/products/add', methods=['POST', "GET"])
@login_required
def add_product():
    """Создание товара"""
    form = ProductForm()
    if form.validate_on_submit():
        photos = []
        pics = request.files.getlist(form.photos.name)
        if pics:
            for picture_upload in pics:
                print(picture_upload.filename)
                if not picture_upload.filename:
                    photos = ['2']
                    break
                if picture_upload.content_type in ('image/png', 'image/jpeg'):
                    photo = io.BytesIO(picture_upload.read())
                    photograph = Image.open(photo)
                    if not check_photo(photograph):
                        return render_template('product_create.html', title='Создание',
                                               form=form,
                                               message='Фотография не подходит по размеру', current_user=current_user,
                                               args=None)
                    photograph.save(photo, format='PNG')
                    response_photo = post(f'http://0.0.0.0:{port}/api/photos', json={
                        'photo': base64.b64encode(photo.getvalue()).decode()
                    }).json()
                    if 'success' not in response_photo.keys():
                        return render_template('product_create.html', title='Создание',
                                               form=form,
                                               message=response_photo['error'], current_user=current_user, args=None)
                    photos.append(str(response_photo['photo_id']))
                else:
                    return render_template('product_create.html', title='Создание',
                                           form=form,
                                           message='Неверный формат файла', current_user=current_user, args=None)
        else:
            photos = ['2']
        if form.actual_address.data:
            radius = -1
        elif form.radius.data:
            radius = form.radius.data
        else:
            radius = 500
        print(get_coordinates(form.geopoint.data))
        response = post(f'http://0.0.0.0:{port}/api/products', json={
            'user_id': current_user.id,
            'name': form.name.data,
            'description': form.description.data if form.description.data else '',
            'cost': form.cost.data,
            'number': form.phone.data if form.phone.data else current_user.mobile_telephone,
            'point': get_coordinates(form.geopoint.data),
            'email': form.email.data if form.email.data else current_user.email,
            'radius': radius,
            'photos': ','.join(photos),
            'category': form.category.data
        }).json()
        print(response)
        if 'success' in response.keys():
            flash('Товар успешно добавлен')
            return redirect('/products')
        else:
            return render_template('product_create.html', title='Создание',
                                   form=form,
                                   message=response['error'], current_user=current_user, args=None)
    print(form.errors)
    return render_template('product_create.html', title='Создание', form=form, current_user=current_user, args=None)


@app.route('/users/<int:user_id>')
def user_profile(user_id):
    """Профиль пользователя"""
    response = get(f'http://0.0.0.0:{port}/api/users/{user_id}').json()
    session = db_session.create_session()
    user = session.query(User).get(user_id)
    if not user:
        abort(404)
    if user.products:
        active = user.products.filter(Product.is_active == 1).order_by(Product.date.desc()).all()
        finished = user.products.filter(Product.is_active == 0).order_by(Product.date.desc()).all()
        active_dict = [item.to_dict(only=('id', 'name', 'user_id', 'description', 'cost', 'is_active', 'photos',
                                          'point_longitude', 'point_latitude', 'radius', 'contact_email',
                                          'contact_number', 'category', 'date')) for item in active]
        for i in range(len(active_dict)):
            if active_dict[i]['date']:
                active_dict[i]['date'] = datetime.strptime(active_dict[i]['date'], '%Y-%m-%d %H:%M')
                print(active_dict[i]['date'])
        finished_dict = [item.to_dict(only=('id', 'name', 'user_id', 'description', 'cost', 'is_active', 'photos',
                                            'point_longitude', 'point_latitude', 'radius', 'contact_email',
                                            'contact_number', 'category', 'date')) for item in finished]
        for i in range(len(finished_dict)):
            if finished_dict[i]['date']:
                finished_dict[i]['date'] = datetime.strptime(finished_dict[i]['date'], '%Y-%m-%d %H:%M')
    else:
        active_dict = []
        finished_dict = []
    if 'user' in response.keys():
        return render_template('profile_user.html', title='Пользователь', parse=response['user'], args=None,
                               active=active_dict, finished=finished_dict, now=datetime.now())
    abort(404)


@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Изменение профиля пользователя"""
    response = get(f'http://0.0.0.0:{port}/api/users/{user_id}').json()
    args = response['user']
    if current_user.id != user_id:
        abort(403)
    form = EditForm()
    if request.method == 'GET':
        form.name.data = args['name']
        form.surname.data = args['surname']
        form.hometown.data = args['hometown']
        form.address.data = args['address']
        form.phone.data = args['mobile_telephone']
    if form.validate_on_submit():
        response = put(f'http://0.0.0.0:{port}/api/users/{user_id}', json={
            'name': form.name.data,
            'surname': form.surname.data,
            'hometown': get_city(form.hometown.data),
            'mobile_telephone': form.phone.data,
            'address': form.address.data,
            'email': args['email'],
            'photo_id': args['photo_id']
        }).json()
        print(response)
        if 'success' in response.keys():
            flash('Изменения сохранены')
            return redirect(f'/users/{user_id}')
        else:
            return render_template('user_edit.html', title='Регистрация',
                                   form=form,
                                   message=response['error'], current_user=current_user, args=None)
    return render_template('user_edit.html', title='Регистрация', form=form, current_user=current_user, args=None)


@app.route('/send_message/<user_id>', methods=['GET', 'POST'])
@login_required
def send_message(user_id):
    """Отправка сообщений"""
    session = db_session.create_session()
    work_user = session.query(User).get(current_user.id)
    user = session.query(User).get(user_id)
    session.commit()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=work_user, recipient=user,
                      body=form.message.data)
        session = db_session.create_session()
        session.merge(msg)
        session.commit()
        flash('Сообщение отправлено!')
        return redirect(f'/users/{user_id}')
    return render_template('send_message.html', title='Отправить сообщение',
                           form=form, user=user, args=None)


@app.route('/products/<int:product_id>')
def watch_product(product_id):
    """Страница объявления"""
    id_check_product(product_id)
    response = get(f'http://0.0.0.0:{port}/api/products/{product_id}').json()
    if 'product' in response.keys():
        return render_template('product.html', args=response['product'], get_address=get_address,
                               title=response['product']['name'])


@app.route('/products/<int:product_id>/buy')
@login_required
def buy_product(product_id):
    """Покупка продукта"""
    response = get(f'http://0.0.0.0:{port}/api/products/{product_id}').json()
    if 'product' in response.keys():
        args = response['product']
        session = db_session.create_session()
        admin = session.query(User).get(1)
        buyer = session.query(User).get(current_user.id)
        seller = session.query(User).get(args['user_id'])
        template = f'Пользователь {buyer.name} {buyer.surname} ' \
                   f'заинтересован в объявлении {args["name"]}. Скоро он напишет!'
        msg = Message(author=admin, recipient=seller,
                      body=template)
        session = db_session.create_session()
        session.merge(msg)
        session.commit()
        flash('Мы оповестили продавца о покупке')
        return redirect(f'/send_message/{seller.id}')


@app.route('/products/<int:product_id>/change_state')
@login_required
def change_state(product_id):
    """Изменение состояния продукта (вкл/выкл)"""
    response = get(f'http://0.0.0.0:{port}/api/products/{product_id}').json()
    print(response)
    args = response['product']
    if args['user_id'] != current_user.id:
        abort(403)
    session = db_session.create_session()
    product = session.query(Product).get(args['id'])
    product.is_active = 1 - int(product.is_active)
    session.merge(product)
    session.commit()
    if not args['is_active']:
        flash('Объявление убрано из скрытых')
    else:
        flash('Объявление скрыто')
    return redirect(f'/products/{product_id}')


@app.route('/messages')
@login_required
def messages():
    """Страница с входящими сообщениями"""
    session = db_session.create_session()
    current_user.last_message_read_time = datetime.utcnow()
    session.merge(current_user)
    session.commit()
    session = db_session.create_session()
    page = request.args.get('page', 1, type=int)
    user = session.query(User).get(current_user.id)
    session.commit()
    next_url, prev_url = None, None
    messages = user.messages_received.order_by(
        Message.timestamp.desc())
    if messages:
        page_cur = SqlalchemyOrmPage(messages, page=page, items_per_page=5)
        if page <= page_cur.item_count:
            next_url = '/messages?page=' + str(page + 1) \
                if page + 1 <= page_cur.page_count else None
            prev_url = '/messages?page=' + str(page - 1) \
                if page > 1 else None
            query = page_cur.items
            print(page, query)
            print(next_url, prev_url)
        else:
            return redirect('/messages?page=' + page_cur.item_count)
    else:
        query = messages.all()
    return render_template('messages.html', messages=query, title='Сообщения',
                           next_url=next_url, prev_url=prev_url, args=None)


@app.route('/products/<int:product_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_product(product_id):
    """Удаление объявления"""
    id_check_product(product_id)
    form = ConfirmForm()
    response = get(f'http://0.0.0.0:{port}/api/products/{product_id}').json()
    args = response['product']
    if args['user_id'] != current_user.id:
        abort(403)
    if form.validate_on_submit():
        response = delete(f'http://0.0.0.0:{port}/api/products/{product_id}').json()
        print(response)
        if 'success' in response.keys():
            flash('Товар успешно удален')
            return redirect('/products')
        flash(f'Опреация не завершена. Причина: {response["error"]}')
        redirect(f'/products/{product_id}/delete')
    return render_template('product_delete.html', title='Удаление', form=form, current_user=current_user, args=None,
                           name=args['name'])


@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """Изменение объявления"""
    id_check_product(product_id)
    form = ProductForm()
    response = get(f'http://0.0.0.0:{port}/api/products/{product_id}').json()
    args = response['product']
    if args['user_id'] != current_user.id:
        abort(403)
    if request.method == "GET":
        session = db_session.create_session()
        form.name.data = args['name']
        form.description.data = args['description']
        form.cost.data = int(args['cost'])
        form.radius.data = int(args['radius']) if args['radius'] > 0 else ''
        if session.query(Category).get(args['category']):
            form.category.data = session.query(Category).get(args['category']).identifier
        else:
            form.category.data = 'no'
        form.geopoint.data = get_address((args['point_longitude'], args['point_latitude']))
        form.actual_address.data = True if args['radius'] < 1 else False
        form.email.data = args['contact_email']
        form.phone.data = args['contact_number']
    if form.validate_on_submit():
        photos = []
        pics = request.files.getlist(form.photos.name)
        if pics:
            for picture_upload in pics:
                print(picture_upload.filename)
                if not picture_upload.filename:
                    photos = ['2']
                    break
                if picture_upload.content_type in ('image/png', 'image/jpeg'):
                    photo = io.BytesIO(picture_upload.read())
                    photograph = Image.open(photo)
                    if not check_photo(photograph):
                        return render_template('product_edit.html', title='Изменение',
                                               form=form,
                                               message='Фотография не подходит по размеру', current_user=current_user,
                                               args=args, get_address=get_address, get_coordinates=get_coordinates)
                    photograph.save(photo, format='PNG')
                    response_photo = post(f'http://0.0.0.0:{port}/api/photos', json={
                        'photo': base64.b64encode(photo.getvalue()).decode()
                    }).json()
                    if 'success' not in response_photo.keys():
                        return render_template('product_edit.html', title='Изменение',
                                               form=form,
                                               message=response_photo['error'], current_user=current_user,
                                               args=args, get_address=get_address, get_coordinates=get_coordinates)
                    photos.append(str(response_photo['photo_id']))
                else:
                    return render_template('product_edit.html', title='Изменение',
                                           form=form,
                                           message='Неверный формат файла', current_user=current_user, args=args,
                                           get_address=get_address, get_coordinates=get_coordinates)
        else:
            photos = ['2']
        if form.actual_address.data:
            radius = -1
        elif form.radius.data:
            radius = form.radius.data
        else:
            radius = 2000
        print(get_coordinates(form.geopoint.data))
        response = put(f'http://0.0.0.0:{port}/api/products/{product_id}', json={
            'user_id': current_user.id,
            'name': form.name.data,
            'description': form.description.data if form.description.data else '',
            'cost': float(form.cost.data),
            'number': form.phone.data if form.phone.data else current_user.mobile_telephone,
            'is_active': args['is_active'],
            'point': get_coordinates(form.geopoint.data),
            'email': form.email.data if form.email.data else current_user.email,
            'radius': radius,
            'photos': ','.join(photos),
            'category': form.category.data
        }).json()
        print(response)
        if 'success' in response.keys():
            flash('Товар успешно изменен')
            return redirect(f'/products/{product_id}')
        else:
            return render_template('product_edit.html', title='Изменение',
                                   form=form,
                                   message=response['error'], current_user=current_user, args=args,
                                   get_address=get_address, get_coordinates=get_coordinates)
    print(form.errors)
    return render_template('product_edit.html', title='Изменение', form=form, current_user=current_user, args=args,
                           get_address=get_address, get_coordinates=get_coordinates)


@app.route('/notifications')
@login_required
def notifications():
    """Уведомления"""
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])


if __name__ == '__main__':
    #  Запуск приложения
    db_session.global_init(os.path.join('db', 'shop.sqlite'))
    app.run(host='0.0.0.0', port=port)
