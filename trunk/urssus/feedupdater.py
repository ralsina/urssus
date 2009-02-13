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

from globals import *

__session__=session

import sys, time, datetime, random, traceback
import elixir
import sqlalchemy as sql
from dbtables import *
import Queue
  
def updateOne(feed):
  feed.update(forced=True)
  
def updateOneNice(feed):
  feed.update()
  
# The feed updater (runs out-of-process)
def feedUpdater():
  import dbtables
  lastCheck=datetime.datetime(1970, 1, 1)
  # Wait blocked until the main thread tells us we can go
  try:
    f=feedUpdateQueue.get(block=True, timeout=10)
  except Queue.Empty:
    pass
  while True:
    try:
      debug("updater loop")
      # See if we have any feed update requests
      try:
        f=feedUpdateQueue.get(block=True, timeout=10)
        info("updating feed %d"%f.id)
        f.update()
      except Queue.Empty:
        debug("No feeds in queue, going to schedule")
        pass
  
      now=datetime.datetime.now()
      period=config.getValue('options', 'defaultRefresh', 1800)
      cutoff=now-datetime.timedelta(seconds=period+random.randint(-60, 60))
      if (now-lastCheck).seconds>30: # Time to see if a feed needs updating
        # Feeds with custom check periods
        debug("Checking feeds with custom update times")
        now_stamp=time.mktime(now.timetuple())
        flist=dbtables.Feed.query.filter(sql.and_(dbtables.Feed.updateInterval<>-1, 
                              sql.func.strftime('%s', dbtables.Feed.lastUpdated, 'utc')+\
                                                      dbtables.Feed.updateInterval*60<now_stamp)).\
                              filter(dbtables.Feed.xmlUrl<>None)
        info("%d feeds are due for custom checking"%flist.count())
        info("Due: %s"%(','.join(f.text for f in flist)))
        for feed in flist:
          info("updating feed %d"%feed.id)
          feed.update()
        # Feeds with default check period
        # Limit to 5 feeds so they get progressively out-of-sync and you don't have a glut of
        # feeds updating all at the same time
        debug("Checking feeds with default update times. Cutoff is %s"%str(cutoff))
        flist=dbtables.Feed.query.filter(sql.and_(dbtables.Feed.updateInterval==-1, 
                                                        dbtables.Feed.lastUpdated < cutoff)).\
                                                        filter(dbtables.Feed.xmlUrl<>None).\
                                                        order_by(dbtables.Feed.lastUpdated)
        info("%d feeds due for default checking"%flist.count())
        if flist.count()<5: lastCheck=now
        for f in flist.limit(5):
          info("updating feed %d"%f.id)
          f.update()
    except:
      info ("crash in feedupdater, recovering")
      traceback.print_exc(file=sys.stderr)
        
def main():
  initDB()
#  elixir.metadata.bind.echo = True
  feedUpdater()
  

if __name__ == "__main__":
  main()
