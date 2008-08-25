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

# Singleton config object

import ConfigParser
import os
from simplejson import dumps, loads

cfdir=os.path.join(os.path.expanduser('~'),'.urssus')
cfname=os.path.join(cfdir,'config')

def getValue(section,key,default=None):
  section=section.lower()
  key=key.lower()
  try:
    return loads(conf.get (section,key))
  except:
    return default

def setValue(section,key,value):
  section=str(section)
  key=str(key)
  section=section.lower()
  key=key.lower()
  value=dumps(value)
  try:
    r=conf.set(section,key,value)
  except ConfigParser.NoSectionError:
    conf.add_section(section)
    r=conf.set(section,key,value)
  f=open(cfname,'w')
  conf.write(f)
  return r


class ConfigError(Exception):
  def __init__(self,modulename,msg):
    self.modulename=modulename
    self.msg=msg


conf=ConfigParser.SafeConfigParser()
if not os.path.isdir(cfdir):
  os.mkdir(cfdir)

if not os.path.isfile(cfname):
  open(cfname, 'w').close()
f=open(cfname,'r')
conf.readfp(f)
f.close()


'''
Configuration options definitions, used to build an automatic config dialog 
(hackers only, regular users get a regular one later).

Do NOT just use them in the sources, define them
here, then use them in the sources.
It's a list of lists, first level is keyed by
section, second level by option.

Do not include things that are not reasonably editable (for example, the widths
of the splitters) or will be overwritten when quitting the app, thus having
no visible effect (window size), or are already "configurable" by choosing them
from the menu (example: showMainBar, viewMode)


The options variable is a list of sections.
A section is a list: (sectionName,options)
Options are a list of Option.
An option is (OptionName, definition)

Definitions are as follow:

('string',    default, help)
('password',  default, help)
('int',       default, help, min,max) # (min==None is no minimum, and the same for max)
('strlist',   default, help)
('intlist',   default, help)
('bool',      default, help)
('choice',    default, help, ('opt1',...,'optn'))

'''

options = (
  ('ui', 
    (
      ('alwaysShowFeed',  ('bool', False, "Always show a link to the post's feed when displaying a post")), 
      ('hideOnTrayClick', ('bool', True, "Hide the main window when clicking on the tray icon")), 
      ('startOnTray', ('bool', False, "Don't show the main window on startup")), 
    )
  ), 
  ('options', 
    (
      ('defaultRefresh'      ,  ('int', 1800, "How often feeds should be refreshed by default (in seconds).", 300, None )), 
      ('maxPostsDisplayed'   ,  ('int', 1000, "Limit the display to this many posts. If set too high, opening 'All Feeds' may take forever", 0, None)), 
      ('defaultExpiration'   ,  ('int',    7, "How long should articles be kept by default. (In days). You need to restart uRSSus to have an effect.", 0, 9999)), 
      ('fetchOnStartup'      ,  ('bool', False, "Fetch all feeds on startup.")), 
      ('showDebugDialog'     ,  ('bool', False, "Show dialog on uncatched exceptions. Only a good idea if you want to help debug uRSSus ;-). You need to restart uRSSus to have an effect.")), 
      ('followLinksInUrssus' ,  ('bool', False, "If True, links in articles will open in uRSSus window, instead of in your web browser. You can still open in the browser by using right click and 'Open in New Window'")), 
    )
  ), 
)

