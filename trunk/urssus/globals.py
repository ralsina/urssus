import processing

# A queue where subprocesses can put status messages, so 
# they appear in the window's statusbar. For example "updating NiceFeed".
statusQueue=processing.Queue()

# A queue with a list of queues to be refreshed in the feed tree
# for example when it's updated by a subprocess
# 
# [0,id] means "mark this feed as updating"
# [1,id] means "finished updating"
# [2,id,parents] means "refresh the text" (for example if you read an article, 
#                         to update the unread count,parents updates all parents)
# [3,id,count] means "notify on the systray icon that there are new articles here
# [4,url] means "add feed with this url"
# [5,fname] means "import fname which is a opml file"

feedStatusQueue=processing.Queue()
