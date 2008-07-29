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
from demjson import JSON

cfdir=os.path.join(os.path.expanduser('~'),'.urssus')
cfname=os.path.join(cfdir,'config')

def getValue(section,key,default=None):
  section=section.lower()
  key=key.lower()
  try:
    return JSON().decode(conf.get (section,key))
  except:
    return default

def setValue(section,key,value):
  section=str(section)
  key=str(key)
  section=section.lower()
  key=key.lower()
  value=JSON().encode(value)
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



