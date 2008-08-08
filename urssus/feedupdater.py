from globals import *
import sys, time, datetime
import elixir
from dbtables import *
  
def updateOne(feed):
  feed.update(forced=True)
  elixir.session.flush()  
  
# The feed updater (runs out-of-process)
def feedUpdater(full=False):
  import dbtables
  if full:
      for feed in dbtables.Feed.query.filter(dbtables.Feed.xmlUrl<>None):
#        feedStatusQueue.put([0, feed.id])
        try: # we can't let this fail or it will stay marked forever;-)
          feed.update()
          time.sleep(1)
        except:
          pass
#        feedStatusQueue.put([1, feed.id])
  else:
    while True:
      info("updater loop")
      now=datetime.datetime.now()
      period=config.getValue('options', 'defaultRefresh', 1800)
      ids=[feed.id for feed in dbtables.Feed.query.filter(dbtables.Feed.xmlUrl<>None)]
      for id in ids :
        time.sleep(1)
        feed=dbtables.Feed.get_by(id=id)
        if feed.updateInterval==0: # Update never
          continue
        elif feed.updateInterval<>-1: # not update default
          period=60*feed.updateInterval # convert to seconds
        if (now-feed.lastUpdated).seconds>period:
          info("updating because of timeout")
          try:
            feed.update()
            # feed.expire(expunge=False)
          except:
            pass
      time.sleep(60)

def main():
  initDB()
  elixir.metadata.bind.echo = True
  feedUpdater(full=len(sys.argv)>1)
  

if __name__ == "__main__":
  main()
