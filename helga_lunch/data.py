from __future__ import unicode_literals

import datetime
import sys

import pymongo
import six

from helga import log
from helga.db import db


logger = log.getLogger(__name__)


class LunchRecord(object):

    def __init__(self, record):
        self.record = record

    @classmethod
    def get_empty_record(cls, business_id, name):
        return cls({
            'business_id': business_id,
            'name': name,
            'last_suggested': None,
            'suggestion_count': 0,
            'last_visited': None,
            'visit_count': 0,
        })

    @classmethod
    def get_latest(cls, limit=5):
        return [
            cls(l) for l in
            db.lunch_location
              .find({'last_visited': {'$ne': None}})
              .sort('last_visited', direction=pymongo.DESCENDING)
              .limit(limit)
        ]

    @classmethod
    def get_top(cls, limit=5):
        return [
            cls(l) for l in
            db.lunch_location
              .find({'visit_count': {'$gt': 0}})
              .sort('visit_count', direction=pymongo.DESCENDING)
              .limit(limit)
        ]

    @classmethod
    def get_by_name(cls, name):
        return [cls(l) for l in db.lunch_location.find({'name': name})]

    @classmethod
    def get_by_id(cls, business_id):
        location = db.lunch_location.find_one({'business_id': business_id})
        if location:
            return cls(location)
        return None

    @classmethod
    def create_if_not_exists(cls, location_id, name):
        location = LunchRecord.get_by_id(location_id)
        if not location:
            location = cls.get_empty_record(location_id, name)
            location.save()

    def visit(self):
        self['last_visited'] = datetime.datetime.utcnow()
        self['visit_count'] = self['visit_count'] + 1
        self.save()

    def save(self):
        db.lunch_location.update(
            {'location_id': self['location_id']},
            self.record,
            upsert=True
        )

    def delete(self):
        db.lunch_location.remove({'location_id': self['location_id']})

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key):
        return self.record[key]

    def __setitem__(self, key, value):
        self.record[key] = value

    def __iter__(self):
        return six.iteritems(self.record)

    def __str__(self):
        if sys.version_info > (3, 0):
            return self.__unicode__()
        return self.__unicode__().encode(sys.getdefaultencoding())

    def __unicode__(self):
        return six.text_type(self.record)

    def __repr__(self):
        return "<Lunch Record '{record}'>".format(
            record=six.text_type(self)
        )
