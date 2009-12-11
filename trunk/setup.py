# -*- coding: utf-8 -*-

# uRSSus, a multiplatform GUI news agregator
# Copyright (C) 2008 Roberto Alsina
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# version 2 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

import os
import sys
from setuptools import setup, find_packages

install_requires= ['SQLAlchemy>=0.5.2',
                   'Elixir>=0.6.1',
                   'simplejson',
                   'pyxml',
                  ]

if sys.version<"2.6":
    install_requires.append("multiprocessing")

setup(
    name="uRSSus",
    packages=['urssus',
      'urssus.ui',
      'urssus.util',
      'urssus.util.GoogleReader',
      'urssus.util.GoogleReader.web',
      'urssus.util.GoogleReader.web.resolvUrl',
      'urssus.templates',
      ],
    version="0.2.13",
    author="Roberto Alsina",
    author_email='ralsina@netmanagers.com.ar',
    package_data = {'urssus.templates': ['*.tmpl', '*.css', '*.js'],
                    'urssus.versioning': ['*.cfg'],
                   },
    entry_points = {'gui_scripts': ['urssus = urssus.main:main'],
        'console_scripts': ['urssus_upgrade_db=urssus.database:main',
        'urssus_client=urssus.client:main',
        ], },
    install_requires = install_requires,
    extras_require = {'Twitter': ["twitter"] },
    description = 'A multiplatform GUI news agregator.',
    license = 'GPLv2',
    keywords = 'atom rss pyqt',
    url = 'http://urssus.googlecode.com',
    long_description = '''
uRSSus is a multi-platform RSS/Atom news aggregator, with a PyQt4 GUI.
The code is hosted at http://urssus.googlecode.com and the license is GPL v2.0.

Hope you enjoy it, please use googlecode's issues_ page for bug reports,
or mail me at ralsina at netmanagers dot com dot ar.

.. _issues: http://code.google.com/p/urssus/issues/list
'''
)

def install_xdg():
    '''On xdg-compliant systems, install desktop file and icon'''
    os.system('xdg-desktop-menu install --novendor  uRSSus.desktop')
    os.system('sudo xdg-icon-resource install --size 128 --novendor %s'%\
              os.path.join('urssus', 'images', 'urssus.png'))
