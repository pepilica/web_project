import requests
import PIL
from flask import jsonify
from flask_restful import abort
from data import db_session
from data.constants import GEOCODER_APIKEY, GEOCODER_API_SERVER
from data.products import Product
from data.users import User


def id_check_product(product_id):
    """Проверка продукта на существование"""
    session = db_session.create_session()
    product = session.query(Product).filter(Product.id == product_id).first()
    session.commit()
    if not product:
        abort(404)


def success():
    """Возвращает json при удачной операции"""
    return jsonify({'success': 'OK'})


def wrong_query():
    """Возвращает json при неправильном запросе"""
    return jsonify({'error': 'Неправильный запрос'})


def blank_query():
    """Возвращает json при пустом запросе"""
    return jsonify({'error': 'Пустой запрос'})


def check_address(address):
    """Проверка адреса"""
    geocoder_params = {
        "apikey": GEOCODER_APIKEY,
        "geocode": address,
        "format": "json"
    }
    response_toponym = requests.get(GEOCODER_API_SERVER, params=geocoder_params)
    if not response_toponym:
        return False, None
    json_response = response_toponym.json()
    toponym = json_response["response"]["GeoObjectCollection"]["featureMember"]
    if not toponym:
        return False, None
    return True, toponym[0]['GeoObject']['metaDataProperty']['GeocoderMetaData']['Text']


def check_photo(image):
    """Проверка фотографии на соответствие размерам"""
    x, y = image.size
    return 200 <= min(x, y) and max(x, y) <= 2000


def get_coordinates(address):
    """Находит кординаты по адресу"""
    geocoder_params = {
        "apikey": GEOCODER_APIKEY,
        "geocode": address,
        "format": "json"
    }
    response_toponym = requests.get(GEOCODER_API_SERVER, params=geocoder_params)
    if not response_toponym:
        return None
    json_response = response_toponym.json()
    toponym = json_response["response"]["GeoObjectCollection"]["featureMember"]
    if not toponym:
        return None
    return toponym[0]['GeoObject']['Point']['pos']


def get_city(coordinates):
    """Находит город/область по координатам/адресу"""
    geocoder_params = {
        "apikey": GEOCODER_APIKEY,
        "geocode": ','.join(map(str, coordinates)) if type(coordinates) != str else coordinates,
        "format": "json"
    }
    response_toponym = requests.get(GEOCODER_API_SERVER, params=geocoder_params)
    if not response_toponym:
        return None
    json_response = response_toponym.json()
    toponym = json_response["response"]["GeoObjectCollection"]["featureMember"]
    if not toponym:
        return None
    tmp = ''
    for i in toponym[0]['GeoObject']['metaDataProperty']['GeocoderMetaData']['Address']['Components']:
        if i['kind'] == 'locality':
            return i['name']
        if i['kind'] == 'area':
            tmp = i['name']
    return tmp


def get_address(coords):
    """Получает адрес по координатам"""
    geocoder_params = {
        "apikey": GEOCODER_APIKEY,
        "geocode": ','.join(map(str, coords)),
        "format": "json"
    }
    response_toponym = requests.get(GEOCODER_API_SERVER, params=geocoder_params)
    if not response_toponym:
        return None
    json_response = response_toponym.json()
    toponym = json_response["response"]["GeoObjectCollection"]["featureMember"]
    if not toponym:
        return None
    print(toponym[0]['GeoObject']['metaDataProperty']['GeocoderMetaData']['Address']['formatted'])
    return toponym[0]['GeoObject']['metaDataProperty']['GeocoderMetaData']['Address']['formatted']