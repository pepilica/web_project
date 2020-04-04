import sqlalchemy
from .db_session import SqlAlchemyBase


class Photo(SqlAlchemyBase):
    __tablename__ = 'photos'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    photo = sqlalchemy.Column(sqlalchemy.BLOB)

    def __repr__(self):
        return f'<Фотография #{self.id}>'
