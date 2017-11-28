from __future__ import unicode_literals

import datetime
import random

import six

from helga import log
from helga.plugins import command, ACKS

from .client import YelpClient, DEFAULT_SEARCH_LIMIT
from .data import LunchRecord


DATE_FORMAT = '%Y %B %d'
DEFAULT_LIMIT = 5
DEFAULT_SUGGESTION = 'Cypress'
MAX_LIMIT = 50
MAX_RADIUS = 40000  # 40,000 m = 40 km, constraint imposed by Yelp API
MAX_QUERIES_PER_SUGGESTION = 5  # only make up to this number of queries to Yelp API for one suggestion
SUGGESTION_REUSE_INTERVAL_IN_DAYS = 14  # don't suggest the same place twice within this threshold


logger = log.getLogger(__name__)


yelp_client = YelpClient()


def get_int(args, index=0, default=DEFAULT_LIMIT):
    try:
        value = int(args[index])
    except (IndexError, ValueError):
        value = default
    return value


def constrain(value, minimum=1, maximum=MAX_LIMIT):
    return max(minimum, min(value, maximum))


def get_kwarg_value(arg):
    return arg.split('=', 1)[1]


def format_business(business):
    categories = ', '.join(business.categories)
    return ('{b.name}, {b.address} ({b.rating}, {b.price}, {b.distance} away)' 
            ' - {categories}').format(b=business, categories=categories)


def parse_search_args(args):
    search_criteria = {}
    for arg in args:
        if arg.lower().startswith('categories='):
            search_criteria['categories'] = get_kwarg_value(arg)
        elif arg.lower().startswith('radius='):
            try:
                radius = int(get_kwarg_value(arg))
            except ValueError:
                return 'Invalid radius!'
            else:
                search_criteria['radius'] = constrain(radius, maximum=MAX_RADIUS)
        elif arg.lower().startswith('term='):
            search_criteria['term'] = get_kwarg_value(arg)
        else:
            return "Invalid criterion: {}".format(arg)
    return search_criteria


def get_new_suggestion(search_criteria):
    businesses = None
    offset = 0
    now = datetime.datetime.utcnow()
    query_count = 0
    suggested_business = None
    while suggested_business is None:
        if not businesses:
            search_criteria['offset'] = offset
            businesses = yelp_client.search(**search_criteria)
            offset += DEFAULT_SEARCH_LIMIT
            query_count += 1
            if not businesses:
                return 'Failed to retrieve businesses from Yelp'

        random_business = random.choice(businesses)
        businesses.remove(random_business)

        if not businesses and query_count == MAX_QUERIES_PER_SUGGESTION:
            # reached query limit, only one business left ... suggest it
            return random_business

        location = LunchRecord.get_by_id(random_business.id)
        # TODO - don't suggest places recently suggested
        if not location \
                or not location['last_visited'] \
                or (now - location['last_visited']).days >= SUGGESTION_REUSE_INTERVAL_IN_DAYS:
            return random_business
    return 'Just go to {}'.format(DEFAULT_SUGGESTION)


def get_suggestion(args):
    # TODO - implement logic to suggest Cypress with probability based on time
    search_criteria = parse_search_args(args)
    if isinstance(search_criteria, six.string_types):
        return search_criteria  # error message

    suggested_business = get_new_suggestion(search_criteria)
    if isinstance(suggested_business, six.string_types):
        return suggested_business   # error message

    LunchRecord.create_if_not_exists(suggested_business.id, suggested_business.name)
    return format_business(suggested_business)


def get_history(args):
    limit = constrain(get_int(args))
    latest_restaurants = LunchRecord.get_latest(limit)
    if not latest_restaurants:
        return 'Nothing to show'
    return [
        '{last_visited}: {name}'.format(last_visited=record['last_visited'].strftime(DATE_FORMAT), name=record['name'])
        for record in LunchRecord.get_latest(limit)
    ]


def get_most_popular(args):
    limit = constrain(get_int(args))
    most_popular_restaurants = LunchRecord.get_top(limit)
    if not most_popular_restaurants:
        return 'Nothing to show'
    return [
        '{index}: {name} ({count} times)'.format(index=i+1, name=record['name'], count=record['visit_count'])
        for i, record in enumerate(most_popular_restaurants)
    ]


def visit_location(args):
    if not args:
        return 'You must provide a restaurant name!'
    name = ' '.join(args)
    locations = LunchRecord.get_by_name(name)
    if len(locations) > 1:
        choices = ['Multiple restaurants matched that name. Use one of the following IDs instead:']
        choices.extend(
            '{name} ({id})'.format(name=location['name'], id=location['location_id'])
            for location in locations
        )
        return choices
    if not locations:
        location = LunchRecord.get_by_id(name)
        if not location:
            return 'Could not find a restaurant matching "{}"'.format(name)
    else:
        location = locations[0]
    location.visit()
    return random.choice(ACKS)


# @command('lunch', aliases=['l', 'food'], help='Ask helga where to eat')
def lunch(client, channel, nick, message, cmd, args):
    # TODO - implement listing of recent suggestions, allow adding restaurants manually?
    if not cmd or cmd in ('suggest', 'search'):
        return get_suggestion(args)
    elif cmd in ('history', 'latest'):
        return get_history(args)
    elif cmd == 'top':
        return get_most_popular(args)
    elif cmd in ('log', 'record'):
        return visit_location(args)
    else:
        return "I don't know about that command, {}".format(nick)
