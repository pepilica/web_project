import requests
import PIL
from flask_restful import abort
from data import db_session
from data.constants import GEOCODER_APIKEY, GEOCODER_API_SERVER
from data.users import User


def check_address(address):
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
    x, y = image.size
    return 200 <= min(x, y) and max(x, y) <= 2000


def get_coordinates(address):
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
