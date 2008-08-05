from globals import *
import sys, time, datetime
import elixir
  
def updateOne(feed):
  feed.update()
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
      time.sleep(60)
      now=datetime.datetime.now()
      for feed in dbtables.Feed.query.filter(dbtables.Feed.xmlUrl<>None):
        period=config.getValue('options', 'defaultRefresh', 1800)
        if feed.updateInterval==0: # Update never
          continue
        elif feed.updateInterval<>-1: # not update default
          period=60*feed.updateInterval # convert to seconds
        if (now-feed.lastUpdated).seconds>period:
          info("updating because of timeout")
#          feedStatusQueue.put([0, feed.id])
          try: # we can't let this fail or it will stay marked forever;-)
            feed.update()
            # While we're at it
            feed.expire(expunge=False)
          except:
            pass
#          feedStatusQueue.put([1, feed.id])
