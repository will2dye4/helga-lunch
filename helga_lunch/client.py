from __future__ import unicode_literals

import os
import sys
import urlparse

from collections import namedtuple

import requests

from helga import log, settings


API_TOKEN_KEY = 'LUNCH_YELP_API_ACCESS_TOKEN'
DEFAULT_LATITUDE = 33.776991
DEFAULT_LONGITUDE = -84.387027
DEFAULT_LOCALE = 'en_US'
DEFAULT_SEARCH_CATEGORIES = 'food'
DEFAULT_SEARCH_LIMIT = 50
DEFAULT_SEARCH_RADIUS = 1000   # 1000 m = 1 km
YELP_API_BASE_URL = getattr(settings, 'LUNCH_YELP_API_BASE_URL', 'https://api.yelp.com').rstrip('/')
YELP_BUSINESS_SEARCH_URL = urlparse.urljoin(YELP_API_BASE_URL, 'v3/businesses/search')


logger = log.getLogger(__name__)


Business = namedtuple('Business', ['id', 'name', 'distance', 'address', 'price', 'rating', 'categories'])


class YelpClient(object):

    def __init__(self):
        token = getattr(settings, API_TOKEN_KEY, os.getenv(API_TOKEN_KEY, ''))
        if not token:
            logger.error('"{}" must be defined!'.format(API_TOKEN_KEY))
            sys.exit(1)
        self.token = token

    def _get_headers(self):
        return {
            'Authorization': 'Bearer {}'.format(self.token)
        }

    @staticmethod
    def _get_business_from_json(business_json):
        return Business(
            id=business_json.get('id'),
            name=business_json.get('name'),
            distance='{} m'.format(int(business_json.get('distance', -1))),
            address=business_json.get('location', {}).get('address1', '<location unknown>'),
            price=business_json.get('price', '<price unknown>'),
            rating='{} stars'.format(business_json.get('rating', '?')),
            categories=[c.get('title') for c in business_json.get('categories', []) if c.get('title')]
        )

    # https://www.yelp.com/developers/documentation/v3/business_search
    def search(self, categories=DEFAULT_SEARCH_CATEGORIES, radius=DEFAULT_SEARCH_RADIUS,
               term=None, limit=DEFAULT_SEARCH_LIMIT, offset=0):
        params = {
            'latitude': DEFAULT_LATITUDE,
            'longitude': DEFAULT_LONGITUDE,
            'locale': DEFAULT_LOCALE,
            'open_now': True,
            'categories': categories,
            'radius': radius,
            'limit': limit,
        }
        if term:
            params['term'] = term
        if offset:
            params['offset'] = offset

        response = requests.get(YELP_BUSINESS_SEARCH_URL, params, headers=self._get_headers())
        if response.status_code != requests.codes.ok:
            logger.error('Failed to perform Yelp business search: got "{}"'.format(response.status_code))
            return None

        response_json = response.json()
        return [
            self._get_business_from_json(business)
            for business in response_json.get('businesses', [])
            if not business.get('is_closed', False)
        ]
