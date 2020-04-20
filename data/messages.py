from datetime import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase


class Message(SqlAlchemyBase):
    """Таблица с сообщениями"""
    __tablename__ = 'messages'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    sender_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    recipient_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    body = sqlalchemy.Column(sqlalchemy.String(140))
    timestamp = sqlalchemy.Column(sqlalchemy.DateTime, index=True, default=datetime.utcnow)

