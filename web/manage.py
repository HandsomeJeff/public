#!/usr/bin/env python
# manage.py
#
# Copyright (C) 2008-2018 Veselin Penev, https://bitdust.io
#
# This file (manage.py) is part of BitDust Software.
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
import os
import sys

if __name__ == "__main__":
    # assume we run from /bitdust/web/
    sys.path.insert(0, os.path.abspath('..'))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "asite.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
