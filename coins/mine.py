#!/usr/bin/env python
# mine.py
#
# Copyright (C) 2008-2016 Veselin Penev, http://bitdust.io
#
# This file (mine.py) is part of BitDust Software.
#
# BitDust is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BitDust Software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with BitDust Software.  If not, see <http://www.gnu.org/licenses/>.
#
# Please contact us if you have any questions at bitdust.io@gmail.com

#------------------------------------------------------------------------------

_Debug = True
_DebugLevel = 10

#------------------------------------------------------------------------------

import time
import random
import string
import json
import hashlib

#------------------------------------------------------------------------------

if __name__ == '__main__':
    import sys
    import os.path as _p
    sys.path.insert(0, _p.abspath(_p.join(_p.dirname(_p.abspath(sys.argv[0])), '..')))

#------------------------------------------------------------------------------

from logs import lg


from userid import my_id

from crypt import key

from lib import utime

from coins import coins_db

#------------------------------------------------------------------------------


def init():
    pass


def shutdown():
    pass

#------------------------------------------------------------------------------


def build_starter(length=5):
    return (''.join(
        [random.choice(string.uppercase + string.lowercase + string.digits)
         for _ in xrange(length)])) + '_'


def build_hash(payload):
    return hashlib.sha1(payload).hexdigest()


def get_hash_complexity(hexdigest, simplification):
    complexity = 0
    while complexity < len(hexdigest):
        if int(hexdigest[complexity], 16) < simplification:
            complexity += 1
        else:
            break
    return complexity


def get_hash_difficulty(hexdigest, simplification=2):
    difficulty = 0
    while True:
        ok = False
        for simpl in xrange(simplification):
            if hexdigest.startswith(str(simpl) * difficulty):
                ok = True
                break
        if ok:
            difficulty += 1
        else:
            break
    return difficulty - 1


def work_on_data_with_known_difficulty(data,
                                       difficulty,
                                       simplification=2,
                                       starter_length=10,
                                       starter_limit=99999,
                                       stop_marker=None):
    data['miner'] = my_id.getLocalID()
    data_dump = json.dumps(data)
    starter = build_starter(starter_length)
    on = 0
    while True:
        if stop_marker is not None and callable(stop_marker):
            if stop_marker():
                return None
        check = starter + str(on)
        if data is not None:
            check += data_dump
        hexdigest = build_hash(check)
        if difficulty != get_hash_complexity(hexdigest, simplification):
            on += 1
            if on > starter_limit:
                starter = build_starter(starter_length)
                on = 0
            continue
        return {
            "starter": starter + str(on),
            "hash": hexdigest,
            "tm": utime.utcnow_to_sec1970(),
            "data": data,
        }


def work_on_data_from_known_hash(data,
                                 prev_hash,
                                 simplification=2,
                                 starter_length=10,
                                 starter_limit=99999,
                                 stop_marker=None):
    data.update({'prev': prev_hash, })
    difficulty = get_hash_difficulty(prev_hash)
    complexity = get_hash_complexity(prev_hash, simplification)
    if difficulty == complexity:
        complexity += 1
        # print 'found golden coin, step up difficulty:', difficulty
    return work_on_data_with_known_difficulty(
        data,
        complexity,
        starter_limit=starter_limit,
        starter_length=starter_length,
        simplification=simplification,
        stop_marker=stop_marker
    )

#------------------------------------------------------------------------------


class MininigCounter(object):

    def __init__(self, max_counts, max_seconds):
        self.max_counts = max_counts
        self.max_seconds = max_seconds
        self.counts = 0
        self.started = int(time.time())

    def marker(self):
        if self.counts >= self.max_counts:
            return True
        if int(time.time()) - self.started > self.max_seconds:
            return True
        self.counts += 1
        return False


def _test():
    try:
        for test_no in xrange(1, 21):
            print 'start test N', test_no
            start = time.time()
            mc = MininigCounter(10**7, 300)
            simplification = 2
            starter_length = 5
            starter_limit = 99999
            coins = 0
            hexhash = ''
            data = {'a': 'b', }
            while True:
                coin = work_on_data_from_known_hash(
                    data,
                    hexhash,
                    simplification=simplification,
                    starter_length=starter_length,
                    starter_limit=starter_limit,
                    stop_marker=mc.marker)
                if not coin:
                    break
                coins += 1
                hexhash = coin['hash']
                print coin

            print coins, 'coins'
            print 'last hash:', hexhash
            print 'complexity riched:', get_hash_complexity(hexhash, simplification)
            print time.time() - start, 'seconds'
            print mc.counts, 'iterations'
            print 'simplification:', simplification
            print

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    init()
    _test()
    shutdown()
