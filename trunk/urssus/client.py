#!/usr/bin/python

import os, sys, socket
from globals import *

if sys.platform=='win32':
  sockaddr=r'\\.\pipe\uRSSus'
else:
  sockaddr=os.path.join(config.cfdir, 'urssus.socket')

from processing import connection

def clientConn():
  try:
    return connection.Client(sockaddr, authkey='urssus')
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
