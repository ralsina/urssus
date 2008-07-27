# -*- coding: utf-8 -*-

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



