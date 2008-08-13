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

if sys.platform=='win32':
  sockaddr=r'\\.\pipe\uRSSus'
else:
  sockaddr=os.path.join(config.cfdir, 'urssus.socket')

def serverConn():
  try:
    server=connection.Listener(sockaddr)
  except socket.error, e:
    if e[0]==98: #Address already in use
      return None
  serverProc=processing.Process(target=theServer, args=(server, ))
  serverProc.setDaemon(True)
  serverProc.start()
  return serverProc

def theServer(server):
  while True:
    info("Listening for connections")
    conn = server.accept()
    info('connection accepted')
    # Process the message as needed
    try:
      d=conn.recv()
    except: #EOFError?
      conn.close()
      continue
    if len(d)>0:
      data=str(d[0])
      # Simple protocol. We get [data].
      # If data starts with http:// it's a feed we want to subscribe.
      # Elif it ends with .opml or .xml it's a OPML file to import.
      if data.lower().startswith('http://'):
        # Pass it to the main process via feedStatusQueue
        feedStatusQueue.put([4, data])
      elif data.lower().endswith('.opml'):
        feedStatusQueue.put([5, data])
    else:
        feedStatusQueue.put([6, None])      
  server.close()

def main():
  global root_feed

  if sys.platform <> 'win32':
    # Try to be the server
    serverProc=serverConn()
    if not serverProc:
      # FIXME: Assume another copy is running
	  err = "Looks like another copy of uRSSus running. If not, try to delete file " +  sockaddr
	  ErrorMessageWidget(err)
	  sys.exit(1)
  
  import dbtables
  import feedupdater
  dbtables.initDB()
  # Start background updater
  p = processing.Process(target=feedupdater.feedUpdater)
  p.setDaemon(True)
  p.start()

  import urssus
  urssus.main()

from PyQt4 import QtGui
class ErrorMessageWidget(QtGui.QWidget):
  def __init__(self,  text):
    app=QtGui.QApplication(sys.argv)
    QtGui.QWidget.__init__(self)
    QtGui.QMessageBox.critical(None, "Error", text, QtGui.QMessageBox.Ok)

if __name__ == "__main__":
  main()
