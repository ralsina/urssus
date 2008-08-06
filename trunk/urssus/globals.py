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

# Configuration
import config

# Logging
if sys.platform=='win32':
  # easylog and Processing on windows == broken
  def dumb(*a, **kw):
    pass
  critical=dumb
  error=dumb
  warning=dumb
  debug=dumb
  info=dumb 
  setLogger=dumb 
  DEBUG=dumb
else:
  from easylog import critical, error, warning, debug, info, setLogger, DEBUG
  setLogger(name='urssus', level=DEBUG)

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

