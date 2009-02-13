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

import os, sys, codecs, datetime, time

VERSION='0.2.10'

import processing

# A queue where subprocesses can put status messages, so 
# they appear in the window's statusbar. For example "updating NiceFeed".
statusQueue=processing.Queue()

# A queue with a list of queues to be refreshed in the feed tree
# for example when it's updated by a subprocess
# 
# [0,id] means "mark this feed as updating"
# [1,id] means "finished updating"
# [2,id,parents] means "refresh the text" (for example if you read an article, 
#                         to update the unread count,parents updates all parents)
# [3,id,count] means "notify on the systray icon that there are new articles here
# [4,url] means "add feed with this url"
# [5,fname] means "import fname which is a opml file"

feedStatusQueue=processing.Queue()

# A queue where you put the feeds that you want fetched.
# To fetch "All feeds" just pass the root feed.
feedUpdateQueue=processing.Queue()

# Configuration
import config

import logging
logger=logging.getLogger('urssus')
logger.setLevel(logging.INFO)
if sys.platform<>'win32':
  #create console handler and set level to debug
  ch = logging.StreamHandler()
  ch.setLevel(logging.INFO)
  formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
  ch.setFormatter(formatter)
  #add ch to logger
  logger.addHandler(ch)

critical=logger.critical
error=logger.error
warning=logger.warn
info=logger.info
debug=logger.debug

logger.critical("Prueba")

# Templates
from util import tenjin

# To convert UTC times (returned by feedparser) to local times
def utc2local(dt):
  return dt-datetime.timedelta(seconds=time.timezone)

# The obvious import doesn't work for complicated reasons ;-)
to_str=tenjin.helpers.to_str
escape=tenjin.helpers.escape
templateEngine=tenjin.Engine()
tmplDir=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
cssFile=os.path.join(tmplDir,'style.css')
mootools_core=os.path.join(tmplDir,'mootools-core.js')
mootools_more=os.path.join(tmplDir,'mootools-more.js')

def renderTemplate(tname, **context):
  context['to_str']=to_str
  context['escape']=escape
  context['mootools_core']=mootools_core
  context['mootools_more']=mootools_more
  context['utc2local']=utc2local
#  codecs.open('x.html', 'w', 'utf-8').write(templateEngine.render(os.path.join(tmplDir,tname), context))
  return templateEngine.render(os.path.join(tmplDir,tname), context)

# References to background processes
import processing
processes=[]


import sqlalchemy, sqlalchemy.orm

session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.create_session)


def RetryOnDBError(fn):
  def new(*args):
    while True:
      try:
        return fn(*args)
        break
      except sqlalchemy.exc.OperationalError:
        debug("retrying")
        pass # Retry
  return new


