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
import config, sqlalchemy
from globals import *
from sqlite3 import dbapi2 as sqlite

dbfile=os.path.join(config.cfdir, 'urssus.sqlite')
dbUrl="sqlite:///%s"%dbfile

def initDB():
  '''Creates the DB if it doesn't exists, 
     Puts the DB under miruku versioning control if needed,
     upgrades to latest schema if needed'''
  # See if the DB exists, or create
  info ("Initializing DB")
#  if os.path.exists(dbfile):
#      pass
#    con = sqlite.connect(dbfile)
#    # If the migrate_version table exists, kill it
#    try:
#      con.execute('drop table migrate_version')
#      con.commit()
#    except:
#      pass
#    # Check if the miruku table exists
#    try:
#      con.execute('select 1 from miruku_track')
#      con.commit()
#      # If we got this far, it is managed by miruku, 
#      # so upgrade and be done with it
#      cmd='miruku upgrade %s urssus.schema.metadata urssus'%dbUrl
#      info ("Running: %s"%cmd)
#      # Miruku is broken for the versions of sqlalchemy I use right now
#      #os.system(cmd)
#      return
#    except:
#      pass
#  # Either it doesn't exist, or it's not managed by miruku.
#  cmd='miruku create %s urssus.schema.metadata urssus'%dbUrl
#  info ("Running: %s"%cmd)
#  # Miruku is broken for the versions of sqlalchemy I use right now
#  #os.system(cmd)
  
def main():
  initDB()

if __name__ == "__main__":
  main()
