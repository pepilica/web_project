import sqlalchemy
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase
from sqlalchemy import orm


class Product(SqlAlchemyBase, SerializerMixin):
    """Таблица с товарами"""
    __tablename__ = 'products'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer,
                                sqlalchemy.ForeignKey("users.id"))
    owner = orm.relation('User')
    date = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    cost = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    category = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('categories.id'))
    is_active = sqlalchemy.Column(sqlalchemy.Boolean)
    photos = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    point_longitude = sqlalchemy.Column(sqlalchemy.Float, nullable=True)
    point_latitude = sqlalchemy.Column(sqlalchemy.Float, nullable=True)
    radius = sqlalchemy.Column(sqlalchemy.Float, nullable=True)
    contact_email = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    contact_number = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    def __repr__(self):
        return f'<Товар - {self.name}>'
