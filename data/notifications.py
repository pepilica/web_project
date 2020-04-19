import json
from time import time
import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm


class Notification(SqlAlchemyBase):
    __tablename__ = 'notifications'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(128), index=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    timestamp = sqlalchemy.Column(sqlalchemy.Float, index=True, default=time)
    payload_json = sqlalchemy.Column(sqlalchemy.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))