from flask import jsonify, request, send_file
from flask.views import MethodView
from flask_restful import reqparse, Api, Resource, abort
from PIL import Image
from data.photos import Photo
from data.users import User
from data import db_session
from io import BytesIO
import base64


def id_check(photo_id):
    session = db_session.create_session()
    photo = session.query(Photo).get(photo_id)
    print(session.query(Photo).all())
    if not photo:
        abort(404, message=f"Photo {photo_id} not found")


class PhotosResource(Resource):
    def get(self, photo_id):
        id_check(photo_id)
        session = db_session.create_session()
        print(session.query(Photo).all())
        photo = session.query(Photo).get(photo_id)
        print(photo.photo)
        return send_file(
                BytesIO(photo.photo),
                mimetype='image/png',
                as_attachment=True,
                attachment_filename='%s.jpg' % photo_id)

    def delete(self, photo_id):
        id_check(photo_id)
        session = db_session.create_session()
        photo = session.query(Photo).get(photo_id)
        session.delete(photo)
        session.commit()
        return jsonify({'OK': 'Success'})


class PhotosListResource(Resource):
    def post(self):
        session = db_session.create_session()
        args = request.json
        photo_get = base64.b64decode(bytes(args['photo'], encoding='utf-8'))
        photo = Photo(photo=photo_get)
        session.add(photo)
        session.commit()
        return jsonify({'success': 'OK', 'photo_id': photo.id})
