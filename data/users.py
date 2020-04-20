import json
from datetime import datetime
import sqlalchemy
from sqlalchemy_serializer import SerializerMixin
from data.messages import Message
from data.notifications import Notification
from .db_session import SqlAlchemyBase
from sqlalchemy import orm
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from data import db_session


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    """Таблица с пользователями"""
    __tablename__ = 'users'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    surname = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    hometown = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    address = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    email = sqlalchemy.Column(sqlalchemy.String,
                              index=True, unique=True, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    mobile_telephone = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, unique=True)
    deals_number = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    rating = sqlalchemy.Column(sqlalchemy.Float, nullable=True)
    photo_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('photos.id'), nullable=True)
    notifications = orm.relation('Notification', backref='user',
                                 lazy='dynamic')
    products = orm.relation("Product", back_populates='owner', lazy='dynamic')
    messages_sent = orm.relationship('Message', foreign_keys='Message.sender_id', backref='author', lazy='dynamic')
    messages_received = orm.relationship('Message', foreign_keys='Message.recipient_id',
                                         backref='recipient', lazy='dynamic')
    last_message_read_time = sqlalchemy.Column(sqlalchemy.DateTime)

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def new_messages(self):
        session = db_session.create_session()
        last_time = self.last_message_read_time or datetime(1900, 1, 1)
        x = session.query(Message).filter_by(recipient=self).filter(
            Message.timestamp > last_time).count()
        session.commit()
        return x

    def add_notification(self, name, data):
        session = db_session.create_session()
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        session.merge(n)
        session.commit()
        return n

    def __repr__(self):
        return f'<Пользователь - {self.name} {self.surname}>'
