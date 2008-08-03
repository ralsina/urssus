import os, sys, socket
from processing import connection
from dbtables import *
from globals import *
from feedupdater import feedUpdater

if sys.platform=='win32':
  sockaddr=r'\\.\pipe\uRSSus'
else:
  sockaddr=os.path.join(config.cfdir, 'urssus.socket')

def serverConn():
  try:
    server=connection.Listener(sockaddr, authkey='urssus')
  except socket.error, e:
    if e[0]==98: #Address already in use
      return None
  serverProc=processing.Process(target=theServer, args=(server, ))
  serverProc.setDaemon(True)
  serverProc.start()
  return serverProc
    
def clientConn():
  try:
    return connection.Client(sockaddr, authkey='urssus')
  except socket.error, e:
    if e[0]==111: # Connection refused, stale socket
      return None
    else:
      print e

def theServer(server):
  while True:
    conn = server.accept()
    info ('connection accepted')
    # Process the message as needed
    d=conn.recv()
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
    conn.close()
  server.close()

def main():
  global root_feed
  root_feed=initDB()

  # Try to be the server
  serverProc=serverConn()
  if not serverProc: # Ok, be the client
    conn=clientConn()
    if not conn and sys.platform<>'win32' and os.path.exists(sockaddr): #Stale socket
      # FIXME: this is a race condition :-(
      os.unlink(sockaddr)
      serverProc=serverConn()
    else:
      conn.send(sys.argv[1:])
      sys.exit(0)
  
  # Start background updater
  p = processing.Process(target=feedUpdater)
  p.setDaemon(True)
  p.start()

  import urssus
  urssus.main()
  
if __name__ == "__main__":
  main()
