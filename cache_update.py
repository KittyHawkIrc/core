import ConfigParser
import anydbm
import os

import dill as pickle

print "Cache updater for <1.3.2 to 1.4.0+"

cfile = open(os.path.join('.', 'kgb.conf'), 'r+b')
config = ConfigParser.ConfigParser()
config.readfp(cfile)


def config_get(module, item, default=False):  # Stolen right from IC
    if config.has_option(module, item):
        return config.get(module, item)
    else:
        return default


print "Reading config file to find cache name"

try:
    cache_name = config.get('main', 'cache')
except:
    cache_name = ".cache"

cache_name = os.path.join('.', cache_name)

if os.path.isfile(cache_name):
    try:
        cache_fd = open(cache_name, 'r+b')
        cache_state = 1
    except:
        try:
            cache_fd = open(cache_name, 'rb')
            cache_state = 2
            print 'Cache load error, read only!'
        except:
            print 'Unable to load cache entirely!'
            exit(1)
else:
    print "No cache found!"
    exit(1)

cache_old = pickle.loads(cache_fd.read())

cache_fd.close()

os.rename(cache_name, '.cache.old')
print "Old cache renamed to .cache.old"

cache_new = anydbm.open('.cache', 'c')

for item in cache_old:
    cache_new[item] = pickle.dumps(cache_old[item])

cache_new.close()

print "New cache saved to .cache!"
