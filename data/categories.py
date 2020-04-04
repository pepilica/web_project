import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm


class Category(SqlAlchemyBase):
    __tablename__ = 'categories'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    category = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)

    def __repr__(self):
        return self.hazard
