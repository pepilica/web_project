from flask import Flask, render_template, redirect, jsonify, make_response
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from flask_restful import Api
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired
from data import db_session
from data.users import User
from flask_wtf import FlaskForm
from requests import post, put
from data.users_resource import UsersListResource, UsersResource
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)
GEOCODER_API_SERVER = "http://geocode-maps.yandex.ru/1.x/"
SEARCH_API_SERVER = "https://search-maps.yandex.ru/v1/"
STATIC_API_SERVER = "http://static-maps.yandex.ru/1.x/"
GEOCODER_APIKEY = '40d1649f-0493-4b70-98ba-98533de7710b'
user_api = Api(app)
user_api.add_resource(UsersResource, '/api/users/<int:user_id>')
user_api.add_resource(UsersListResource, '/api/users')


class RegisterForm(FlaskForm):
    surname = StringField('Фамилия', validators=[DataRequired()])
    name = StringField('Имя', validators=[DataRequired()])
    email = EmailField('E-mail', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    hometown = StringField('Город проживания', validators=[DataRequired()])
    address = StringField('Адрес', validators=[DataRequired()])
    mobile_telephone = StringField('Мобильный телефон', validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться!')


class LoginForm(FlaskForm):
    email = EmailField('E-mail', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти!')


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
        response = post('http://127.0.0.1:8080/api/users', json={
            'name': form.name.data,
            'surname': form.surname.data,
            'hometown': form.hometown.data,
            'mobile_telephone': form.mobile_telephone.data,
            'address': form.address.data,
            'email': form.email.data,
            'password': form.password.data
        }).json()
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
        if 'OK' in response.keys():
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


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


if __name__ == '__main__':
    db_session.global_init(os.path.join('db', 'shop.sqlite'))
    app.run(port=8080, host='127.0.0.1')

