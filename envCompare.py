#!/usr/bin/env python
import yaml
import pprint
from deepdiff import DeepDiff
import requests
from jsonpath_rw import jsonpath, parse
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


def filterJson(obj,path,values):
    jsonpath_expr = parse(path)
    if isinstance(obj, list):
        myobj = []
        for item in obj:
            matches = [match.value for match in jsonpath_expr.find(item)]
            if matches and matches[0] in values:
                myobj.append(item)
        return myobj

def ignoreFields(listOfFields):
  #['id','trigger.id',action.contextId]
  #{"root['id']","root['trigger']['id']","root['action']['contextId']"}
  rfields = []
  for field in listOfFields:
      fieldsplit = field.split(".")
      rfields.append("root['%s']" % "']['".join(fieldsplit))
  return {f for f in rfields}

def get_json(endpoint,filter=None):
    try:
        r = requests.get(endpoint)
        if r.status_code == requests.codes.ok:
            print r.url
            if not filter:
                return r.json()
            else:
                return filterJson(r.json(),)
    except ValueError as e:
        if "No JSON object could be decoded" in str(e):
            return {}

yaml_file = 'CVP.yaml'
with open(yaml_file, 'r') as f:
    config = yaml.load(f)

urls = []

for env in config['Environments']:
    url = "http://%s:%s" % (env['dryad-core'],env['dryad-port'])
    urls.append(url)

first_obj = None
second_obj = None

items = {}
diffs = {}

for module in config['modules']:

    for dryad_function,details in  module.iteritems():
        items[dryad_function] = {}
        for dryad_element in details.keys():
            first_obj = {}
            second_obj = {}

            pp.pprint(dryad_element)
            items[dryad_function][dryad_element] = { 'urls':[], 'json_data':{'first':{'raw':{},'filtered':{}},'second':{'raw':{},'filtered':{}}}}

            match_fields = details[dryad_element]['match_fields']
            ignore = details[dryad_element]['ignore_fields'] if 'ignore_fields' in  details[dryad_element].keys() \
                else []
            items[dryad_function][dryad_element]['match_fields'] = details[dryad_element]['match_fields']


            for u in urls:
                endpoint = "%s/%s" % (u,details[dryad_element]['path'])
                items[dryad_function][dryad_element]['urls'].append(u)
                if not first_obj:
                    first_obj = get_json(endpoint)
                    items[dryad_function][dryad_element]['json_data']['first']['raw'] = first_obj
                else:
                    items[dryad_function][dryad_element]['json_data']['second']['raw'] = first_obj
                    second_obj = get_json(endpoint)

            if 'filters' in details[dryad_element].keys():
                for path in details[dryad_element]['filters'].keys():

                    first_obj = filterJson(first_obj,path,details[dryad_element]['filters'][path])
                    items[dryad_function][dryad_element]['json_data']['first']['filtered'] = first_obj
                    second_obj = filterJson(second_obj, path, details[dryad_element]['filters'][path])
                    items[dryad_function][dryad_element]['json_data']['second']['filtered'] = second_obj



            for item in first_obj:
                for field in match_fields:
                    if field in item.keys():
                        match = item[field]
                        diffs[match] = []
                        for second_item in second_obj:
                            if field in second_item.keys():
                                if match ==  second_item[field]:
                                    fields = ignore
                                    diff = DeepDiff(item,second_item,ignore_order=True,exclude_paths=ignoreFields(fields))
                                    if diff:
                                        print "Found  Difference{s) in %s" % item[field]
                                        diffs[match].append(diff)
                                        pp.pprint(diff)

                            else:
                                print "No matching item found"


