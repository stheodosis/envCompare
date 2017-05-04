#!/usr/bin/env python
import yaml
import pprint
from deepdiff import DeepDiff
import requests
from operator import itemgetter, attrgetter
from json_delta import load_and_diff, udiff, diff
import sys
import json


pp = pprint.PrettyPrinter(indent=2)

def sort_by_key(obj,key):
    return sorted(obj, reverse=True, key=itemgetter(key))

def deleteKeys(obj,trash):
    if isinstance(obj,list):
        myobj = []
        for item in obj:
            if not isinstance(item,dict):
                continue
            myitem = {}
            for k,v in item.iteritems():
                if k not in trash:
                    myitem[k] = v
            myobj.append(myitem)
    return myobj

def extract_name(obj):
    try:
        return  obj['name']
    except KeyError:
        return 0

def extract_key(obj):
    try:
        return  obj['key']
    except KeyError:
        return 0



def traverse(obj, path=None, callback=None):
    """
    Traverse an arbitrary Python object structure (limited to JSON data
    types), calling a callback function for every element in the structure,
    and inserting the return value of the callback as the new value.
    """
    if path is None:
        path = []

    if isinstance(obj, dict):
        value = {k: traverse(v, path + [k], callback)
                 for k, v in obj.items()}
    elif isinstance(obj, list):
        value = [traverse(elem, path + [[]], callback)
                 for elem in obj]
    else:
        value = obj

    if callback is None:
        return value
    else:
        return callback(path, value)


def traverse_modify(obj, target_path, action):
    """
    Traverses an arbitrary object structure and where the path matches,
    performs the given action on the value, replacing the node with the
    action's return value.
    """
    target_path = to_path(target_path)

    def transformer(path, value):
        if path == target_path:
            return action(value)
        else:
            return value

    return traverse(obj, callback=transformer)


def to_path(path):
    """
    Helper function, converting path strings into path lists.
        >>> to_path('foo')
        ['foo']
        >>> to_path('foo.bar')
        ['foo', 'bar']
        >>> to_path('foo.bar[]')
        ['foo', 'bar', []]
    """
    if isinstance(path, list):
        return path  # already in list format

    def _iter_path(path):
        for parts in path.split('[]'):
            for part in parts.strip('.').split('.'):
                yield part
            yield []

    return list(_iter_path(path))[:-1]


def get_json(endpoint,exclude=None):
    try:
        r = requests.get(endpoint)
        if r.status_code == requests.codes.ok:
            print r.url
            if not exclude:
                return r.json()
            else:
                return deleteKeys(r.json(),exclude)
    except ValueError as e:
        if "No JSON object could be decoded" in str(e):
            return {}

yaml_file = 'CVP.yaml'
with open(yaml_file, 'r') as f:
    config = yaml.load(f)

host = "%s:%s" % (config['Environments'][0]['dryad-core'],config['Environments'][0]['dryad-port'])
hosts = ["%s:%s" % (h['dryad-core'],h['dryad-port']) for h in config['Environments']]

endpoints = []
details = {}
for m in config['modules'].keys():
    for o in config['modules'][m]:
        for a in config['modules'][m][o]:
            endpoints.append('/'.join([m,o,a]))




for e in endpoints:
    urls = ("http://%s/%s" % (hosts[0],e),"http://%s/%s" % (hosts[1],e))
    json1 = get_json(urls[0],exclude=['batchProcessId',u'keywordId',u'id',u'identifier',u'shortCodeId',u'uri',u'contextId',u'endpointId',u'shortcode',u'dependencyRouteId',u'additionalParameters',u'outboundRouteId'])
    json2 = get_json(urls[1],exclude=['batchProcessId',u'keywordId',u'id',u'identifier',u'shortCodeId',u'uri',u'contextId',u'endpointId',u'shortcode',u'dependencyRouteId',u'additionalParameters',u'outboundRouteId'])
    json1sorted = sort_by_key(json1,'description')
    json2sorted = sort_by_key(json2, 'description')

    delta = diff(json1sorted,json2sorted)
    pp.pprint(delta)
    """
    diff = DeepDiff(json1sorted, json2sorted, ignore_order=True)


    print " ====== Examing endpoint %s" % e
    pp.pprint(diff)
    added = []
    removed = []

    if diff:
        try:
            if 'iterable_item_added' in diff.keys():
                for a in diff['iterable_item_added'].keys():
                    #pp.pprint(diff['iterable_item_added'][a])
                    added.append(diff['iterable_item_added'][a])

            if 'iterable_item_removed' in diff.keys():
                for r in diff['iterable_item_removed'].keys():
                    #pp.pprint(diff['iterable_item_removed'][r])
                    removed.append(diff['iterable_item_removed'][r])

        except (KeyError,AttributeError) as e:
            print str(e),type(e)
            sys.exit(0)
    else:
        print " ====== No diffrence found"
    """

#for host in details.keys():
#    for endpoint in details[host].keys():
#        print endpoint

