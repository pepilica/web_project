import base64
import io
import os
from datetime import datetime
from paginate_sqlalchemy import SqlalchemyOrmPage
from PIL import Image
from flask import Flask, render_template, redirect, jsonify, make_response, request, flash, url_for, current_app, \
    get_flashed_messages
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
from flask_restful import Api
from flask_wtf import FlaskForm
from requests import post, put, get
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FileField, TextAreaField, IntegerField, \
    RadioField, MultipleFileField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from data.categories import Category
from data import db_session
from data.messages import Message
from data.photos_resource import PhotosListResource, PhotosResource
from data.products_resource import ProductsResource, ProductsListResource
from data.users import User
from data.users_resource import UsersListResource, UsersResource
from data.utils import check_photo, get_coordinates, get_city, get_address
from data.constants import CATEGORIES, POSTS_PER_PAGE, SORT_BY
port = int(os.environ.get("PORT", 5000))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)
user_api = Api(app)
user_api.add_resource(UsersResource, '/api/users/<int:user_id>')
user_api.add_resource(UsersListResource, '/api/users')
user_api.add_resource(PhotosResource, '/api/photos/<int:photo_id>')
user_api.add_resource(PhotosListResource, '/api/photos')
user_api.add_resource(ProductsResource, '/api/products/<int:product_id>')
user_api.add_resource(ProductsListResource, '/api/products')


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
    session = db_session.create_session()
    return session.query(User).get(user_id)


@app.route('/register', methods=['POST', 'GET'])
def register():
    if current_user.is_authenticated:
        return redirect('/')
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Register',
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
                    return render_template('register.html', title='Register',
                                           form=form,
                                           message='Фотография не подходит по размеру', current_user=current_user,
                                           args=None)
                photograph.save(photo, format='PNG')
                response_photo = post(f'https://0.0.0.0:{port}/api/photos', json={
                    'photo': base64.b64encode(photo.getvalue()).decode()
                }).json()
                photo_output = response_photo['photo_id']
                if 'success' not in response_photo.keys():
                    return render_template('register.html', title='Register',
                                           form=form,
                                           message=response_photo['error'], current_user=current_user, args=None)
            else:
                return render_template('register.html', title='Register',
                                       form=form,
                                       message='Неверный формат файла', current_user=current_user, args=None)
        response = post(f'https://0.0.0.0:{port}/api/users', json={
            'name': form.name.data,
            'surname': form.surname.data,
            'hometown': form.hometown.data,
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
            return render_template('register.html', title='Register',
                                   form=form,
                                   message=response['error'], current_user=current_user, args=None)
    return render_template('register.html', title='Register', form=form, current_user=current_user, args=None)


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        print(0)
        return redirect('/')
    form = LoginForm()
    if form.validate_on_submit():
        response = put(f'https://0.0.0.0:{port}/api/users', json={
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
            return render_template('login.html', title='Login',
                                   form=form,
                                   message=response['error'], current_user=current_user, args=None)
    return render_template('login.html', title='Login',
                           form=form, current_user=current_user, args=None)


@app.route('/')
@app.route('/index')
def main():
    return render_template('base.html', title='Index', current_user=current_user, args=None)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/products', methods=['POST', 'GET'])
def products_main():
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
    response = get(f'https://0.0.0.0:{port}/api/products', json=json_file).json()
    if 'product' in response.keys():
        return render_template('products.html', products=response['product'], next_url=response['next_url'],
                               prev_url=response['prev_url'], session=db_session.create_session(),
                               length=len(response['product']), User=User, Category=Category, int=int, form=form,
                               get_city=get_city, args=None)
    return redirect('/products')


@app.route('/products/add', methods=['POST', "GET"])
@login_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        print()
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
                        return render_template('register.html', title='Register',
                                               form=form,
                                               message='Фотография не подходит по размеру', current_user=current_user,
                                               args=None)
                    photograph.save(photo, format='PNG')
                    response_photo = post(f'https://0.0.0.0:{port}/api/photos', json={
                        'photo': base64.b64encode(photo.getvalue()).decode()
                    }).json()
                    if 'success' not in response_photo.keys():
                        return render_template('register.html', title='Register',
                                               form=form,
                                               message=response_photo['error'], current_user=current_user, args=None)
                    photos.append(str(response_photo['photo_id']))
                else:
                    return render_template('register.html', title='Register',
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
        response = post(f'https://0.0.0.0:{port}/api/products', json={
            'user_id': current_user.id,
            'name': form.name.data,
            'description': form.description.data if form.description.data else '',
            'cost': form.cost.data,
            'number': form.phone.data if form.phone.data else current_user.phone,
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
            return render_template('product_create.html', title='Register',
                                   form=form,
                                   message=response['error'], current_user=current_user, args=None)
    print(form.errors)
    return render_template('product_create.html', title='Register', form=form, current_user=current_user, args=None)


@app.route('/users/<int:user_id>')
def user_profile(user_id):
    response = get(f'https://0.0.0.0:{port}/api/users/{user_id}').json()
    if 'user' in response.keys():
        return render_template('profile_user.html', title='Пользователь', parse=response['user'], args=None)


@app.route('/send_message/<user_id>', methods=['GET', 'POST'])
@login_required
def send_message(user_id):
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
    return render_template('send_message.html', title='Send Message',
                           form=form, user=user, args=None)


@app.route('/products/<int:product_id>')
def watch_product(product_id):
    response = get(f'https://0.0.0.0:{port}/api/products/{product_id}').json()
    if 'product' in response.keys():
        return render_template('product.html', args=response['product'], get_address=get_address)


@app.route('/messages')
@login_required
def messages():
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
    return render_template('messages.html', messages=query,
                           next_url=next_url, prev_url=prev_url, args=None)


if __name__ == '__main__':
    db_session.global_init(os.path.join('db', 'shop.sqlite'))
    app.run(host='0.0.0.0', port=port, debug=True)
