#!/usr/bin/python
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
from globals import *
import dbus

def main():
  try:
    bus = dbus.SessionBus()
    remote_object = bus.get_object("org.urssus.service", "/uRSSus")
    iface = dbus.Interface(remote_object, "org.urssus.interface")
    
    # FIXME: implement real CLI parsing
    
    if len(sys.argv)==1: # No arguments
      remote_object.show()
    elif sys.argv[1].startswith('http:') or sys.argv[1].startswith('feed:'):
      remote_object.AddFeed(sys.argv[1])
    else:
      remote_object.importOPML(sys.argv[1])
  except dbus.exceptions.DBusException, e:
    if 'ServiceUnknown' in str(e):
      warning(str(e))
      warning("Starting urssus")
      os.execlp('urssus', *sys.argv)
    else:
      error(str(e))

if __name__ == "__main__":
  main()
