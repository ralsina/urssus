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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import os, sys
import migrate.versioning.api as migrate
import config, sqlalchemy
from globals import *

dbfile=os.path.join(config.cfdir, 'urssus.sqlite')
dbUrl="sqlite:///%s"%dbfile
repo=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'versioning')

def initDB():
  '''Creates the DB if it doesn't exists, 
     Puts the DB under migrate versioning control if needed,
     upgrades to latest schema if needed'''
  # See if the DB exists, or create
  info ("Initializing DB")
  if not os.path.exists(dbfile):
    info ("Starting on schema version 0")
    migrate.version_control (dbUrl, repo, version=0 )
  try:
    curVer=migrate.db_version(dbUrl, repo)
    info ("Currently on schema version %d", curVer)
  except sqlalchemy.exceptions.NoSuchTableError:
    info ("Starting on schema version 1")
    # Start at version 1 because this was created by a pre-migrate urssus
    migrate.version_control (dbUrl, repo, version=1 )
  migrate.upgrade(dbUrl, repo)
 
def main():
  initDB()

if __name__ == "__main__":
  main()
