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
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FileField, TextAreaField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Length
from data.constants import POSTS_PER_PAGE

from data import db_session
from data.messages import Message
from data.photos_resource import PhotosListResource, PhotosResource
from data.products_resource import ProductsResource, ProductsListResource
from data.users import User
from data.users_resource import UsersListResource, UsersResource
from data.utils import check_photo

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


class RegisterForm(FlaskForm):
    surname = StringField('Фамилия', validators=[DataRequired()])
    name = StringField('Имя', validators=[DataRequired()])
    email = EmailField('E-mail', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    hometown = StringField('Город проживания', validators=[DataRequired()])
    address = StringField('Адрес', validators=[DataRequired()])
    mobile_telephone = StringField('Мобильный телефон', validators=[DataRequired()])
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


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(User).get(user_id)


@app.route('/register', methods=['POST', 'GET'])
def register():
    if current_user.is_authenticated:
        print(0)
        return redirect('/')
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Register',
                                   form=form,
                                   message="Пароли не сходятся", current_user=current_user)
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
                                           message='Фотография не подходит по размеру', current_user=current_user)
                photograph.save(photo, format='PNG')
                response_photo = post('http://127.0.0.1:8080/api/photos', json={
                    'photo': base64.b64encode(photo.getvalue()).decode()
                }).json()
                photo_output = response_photo['photo_id']
                if 'success' not in response_photo.keys():
                    return render_template('register.html', title='Register',
                                           form=form,
                                           message=response_photo['error'], current_user=current_user)
            else:
                return render_template('register.html', title='Register',
                                       form=form,
                                       message='Неверный формат файла', current_user=current_user)
        response = post('http://127.0.0.1:8080/api/users', json={
            'name': form.name.data,
            'surname': form.surname.data,
            'hometown': form.hometown.data,
            'mobile_telephone': form.mobile_telephone.data,
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
                                   message=response['error'], current_user=current_user)
    return render_template('register.html', title='Register', form=form, current_user=current_user)


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        print(0)
        return redirect('/')
    form = LoginForm()
    if form.validate_on_submit():
        response = put('http://127.0.0.1:8080/api/users', json={
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
                                   message=response['error'], current_user=current_user)
    return render_template('login.html', title='Login',
                           form=form, current_user=current_user)


@app.route('/')
@app.route('/index')
def main():
    return render_template('base.html', title='Index', current_user=current_user)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/products', methods=['POST', 'GET'])
def products_main():
    pass


@app.route('/users/<int:user_id>')
def user_profile(user_id):
    response = get(f'http://127.0.0.1:8080/api/users/{user_id}').json()
    if 'user' in response.keys():
        return render_template('profile_user.html', title='Пользователь', parse=response['user'])


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
                           form=form, user=user)


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
                           next_url=next_url, prev_url=prev_url)


if __name__ == '__main__':
    db_session.global_init(os.path.join('db', 'shop.sqlite'))
    app.run(port=8080, host='127.0.0.1')
