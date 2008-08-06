import os, sys, socket
from processing import connection
from globals import *

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

  # Try to be the server
  serverProc=serverConn()
  if not serverProc:
    # FIXME: Assume another copy is running
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
  
if __name__ == "__main__":
  main()
