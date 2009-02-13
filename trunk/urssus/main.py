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

import os, sys, socket
from processing import connection
from globals import *
from util.backup import backup_files

def main():
  global root_feed
  
  # Backup the DB and config file
  info ("Backing up %s"%config.cfdir)
  backup_files(config.cfdir)
  import dbtables
  import feedupdater
  dbtables.initDB()
  # Start background updater
  p = processing.Process(target=feedupdater.feedUpdater)
  p.setDaemon(True)
  p.start()
  info("Updater PID: %d"%p.getPid())
  import urssus
  urssus.main()

if __name__ == "__main__":
  main()
