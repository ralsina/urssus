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

if sys.platform=='win32':
  sockaddr=r'\\.\pipe\uRSSus'
else:
  sockaddr=os.path.join(config.cfdir, 'urssus.socket')

from processing import connection

def clientConn():
  try:
    return connection.Client(sockaddr)
  except socket.error, e:
    print e
    if e[0]==111: # Connection refused, stale socket
      if sys.platform<>'win32':
        os.unlink(sockaddr)
        return None
      sys.exit(15)


def main():
  conn=clientConn()
  if not conn:
    # Try one more because of the stale socket chance
    pass
  conn=clientConn()
  if not conn: # Start the app
    # FIXME: this is a race condition :-(
    os.execvp('urssus', sys.argv)
  conn.send(sys.argv[1:])
  sys.exit(0)

if __name__ == "__main__":
  main()
