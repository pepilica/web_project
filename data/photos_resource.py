from flask import jsonify, request, send_file
from flask_restful import Resource, abort
from data.photos import Photo
from data import db_session
from io import BytesIO
import base64

from data.utils import success


def id_check(photo_id):
    """Проверка ID на валидность"""
    session = db_session.create_session()
    photo = session.query(Photo).get(photo_id)
    print(session.query(Photo).all())
    if not photo:
        abort(404, message=f"Photo {photo_id} not found")


class PhotosResource(Resource):
    """Работа с фотографией"""
    def get(self, photo_id):
        """Получение фотографии"""
        id_check(photo_id)
        session = db_session.create_session()
        photo = session.query(Photo).get(photo_id)
        return send_file(
                BytesIO(photo.photo),
                mimetype='image/png',
                as_attachment=True,
                attachment_filename='%s.jpg' % photo_id)

    def delete(self, photo_id):
        """Удаление фотографии"""
        id_check(photo_id)
        if photo_id != 1 and photo_id != 2:
            session = db_session.create_session()
            photo = session.query(Photo).get(photo_id)
            session.delete(photo)
            session.commit()
            return success()
        return jsonify({'error': 'Операция запрещена'})


class PhotosListResource(Resource):
    """Работа со списком фотографий"""
    def post(self):
        """Создание фотографии"""
        session = db_session.create_session()
        args = request.json
        photo_get = base64.b64decode(bytes(args['photo'], encoding='utf-8'))
        photo = Photo(photo=photo_get)
        session.add(photo)
        session.commit()
        return jsonify({'success': 'OK', 'photo_id': photo.id})
