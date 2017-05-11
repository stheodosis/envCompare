#!/usr/bin/env python
import yaml
import pprint
from os import walk
from deepdiff import DeepDiff
from jsonpath_rw import parse
import argparse
import logging
import sys

def ignoreFields(listOfFields):

    rfields = []
    for field in listOfFields:
        fieldsplit = field.split(".")
        rfields.append("root['%s']" % "']['".join(fieldsplit))
    return {f for f in rfields}


def findKey(obj,mypath):
    patterns = ['*..path']

    for p in patterns:
        path = p.replace('path',mypath)
        log.debug("Finding key: %s" % path)
        jsonpath_expr = parse(path)
        matches = [(str(match.full_path),match.value,match.context.value) for match in jsonpath_expr.find(obj)]
        log.debug("Matched Values: %s" % ['%s:%s' % (str(m[0]),m[1]) for m in matches])

        if matches:
            return matches
        else:
            log.debug("Did not find any item in path: %s " % path)
            return False

if __name__ == '__main__':
    diffs = {}

    arg = argparse.ArgumentParser('Dryad Yaml Configuration Diff tool')
    arg.add_argument('--prd', help='Path to PRD configuration Directory', required=True)
    arg.add_argument('--bt', help='Path to BT configuration Directory', required=True)
    arg.add_argument('-f', '--fields' , help='Fields names to identify Yaml entities',
                     nargs='*', default=['name','key','description'])
    arg.add_argument('-i', '--ignore', help='Field names to ommit from diff',
                     nargs='*', default=['uri','identifier', 'throttling', 'delay'])
    arg.add_argument('-m', '--modules', help="Specify Dryad Modules",
                     nargs='*', default=[])
    arg.add_argument('-v','--verbose', help="Verbosity Level",
                     action="count", default=0)


    args = arg.parse_args()
    log = logging.getLogger()
    formater = logging.Formatter('%(message)s')


    if args.verbose == 0:
        log.setLevel(logging.CRITICAL)
    elif args.verbose == 1:
        log.setLevel(logging.WARNING)
    elif args.verbose == 2:
        log.setLevel(logging.INFO)
    else:
        log.setLevel(logging.DEBUG)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(formater)
    log.addHandler(consoleHandler)

    btpath = args.bt #"/tmp/cvp/bt01/"
    prdpath = args.prd # "/tmp/cvp/prd/"
    matches = args.fields #['name', 'key', 'description']

    ignore_fields = args.ignore #['identifier', 'uri', 'throttling', 'delay']

    pp = pprint.PrettyPrinter(indent=4)
    f = []
    for (dirpath, dirnames, filenames) in walk(btpath):
            f.extend(filenames)

    for filename in filenames:

        file, extension = filename.split('.')
        if (args.modules and not file in args.modules) or (extension not in ['yaml','yml']):
            continue
        diffs[file] = {}
        bt_ordered = {}
        prd_ordered = {}

        bt_yaml = "%s/%s" % (btpath , filename)
        prd_yaml = "%s/%s" % (prdpath , filename)
        try:
            with open(bt_yaml) as b:
                bt_json = yaml.load(b)
            with open(prd_yaml) as p:
                prd_json = yaml.load(p)
        except Exception as e:
            log.critical("Could not parse Yaml file %s" % filename)
            log.critical("Got error: %s" % str(e))
            continue

        for m in  matches:

            if findKey(bt_json, m):
                bt_paths = findKey(bt_json, m)
                prd_paths = findKey(prd_json, m)
                break
            else:
                bt_paths = None
                prd_paths = None

        if bt_paths:
            for path in bt_paths:
                log.debug("%s:%s" % (path[1],path[2]))
                bt_ordered[path[1]] = path[2]
        else:
            log.info("Did not find  any of match patterns in bt environment in %s" % filename)

        if prd_paths:
            for path in prd_paths:
                prd_ordered[path[1]]=path[2]
        else:                                                                                 
            log.info("Did not find anything on match patterns in Production environment in %s" % filename)
            
        keysdiff = DeepDiff(bt_ordered.keys(),prd_ordered.keys(),ignore_order=True)
        for item in bt_ordered.keys():
            if(item in prd_ordered.keys()):
                order = False if isinstance(bt_ordered[item],list) else True
                diff = DeepDiff(bt_ordered[item],prd_ordered[item],ignore_order=order ,exclude_paths=ignoreFields(ignore_fields))
                if diff:
                    diffs[file] = { item:diff }
        if 'iterable_item_removed' in keysdiff.keys():
            diffs[file]['removed'] = []
            for key,value in keysdiff['iterable_item_removed'].iteritems():
                diffs[file]['removed'].append(value)

        if 'iterable_item_added' in keysdiff.keys():
            diffs[file]['added'] = []
            for key,value in keysdiff['iterable_item_added'].iteritems():
                diffs[file]['added'].append(value)


    for module in diffs.keys():
        if diffs[module]:
            for item in diffs[module].keys():
                if 'added' == item:
                    log.critical("Found %s new item(s) in %s on Production" % (len(diffs[module]['added']),module))
                    log.warning(diffs[module]['added'])
                elif 'removed' == item:
                    log.critical("Found %s items in %s on BT but not on Production" % (len(diffs[module]['removed']),module))
                    log.warning(diffs[module]['removed'])
                else:
                    for type in diffs[module][item]:
                        log.critical("Found Diffrence in %s -> %s : %s " % (module,item,type))
                        log.warning(diffs[module][item][type])
                #else:
                #    print "+++++++++++++++++++++++++= %s =++++++++++++++++++++++++++" % item
                #    pass

                #pp.pprint(diffs[module][item])
