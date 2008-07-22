# -*- coding: utf-8 -*-

import sys, os, time
from datetime import datetime, timedelta

# Templates
from mako.template import Template
from mako.lookup import TemplateLookup
# FIXME: when deploying make this work
tmplLookup=TemplateLookup(directories='templates')

# References to background processes
import processing
processes=[]

# A queue where subprocesses can put status messages, so 
# they appear in the window's statusbar. For example "updating NiceFeed".
statusQueue=processing.Queue()

# A queue with a list of queues to be refreshed in the feed tree
# for example when it's updated by a subprocess
# 
# [0,id] means "mark this feed as updating"
# [1,id] means "finished updating"
# [2,id] means "refresh the text" (for example if you read an article, 
#                                  to update the unread count)

feedStatusQueue=processing.Queue()

# Mark Pilgrim's feed parser
import feedparser as fp

def detailToAuthor(ad):
  '''Converts something like feedparser's author_detail into a 
  nice string describing the author'''

  if 'name' in ad:
    author=ad['name']
    if 'href' in ad:
      author='<a href="%s">%s</a>'%(ad['href'], author)
  if 'email' in ad:
    email ='<a href="mailto:%s">%s</a>'%(ad['email'], ad['email'])
  else:
    email = ''

  if email and author:
    return '%s - %s'%(author, email)
  elif email:
    return email
  return author

# DB Classes
from elixir import * 
import sqlalchemy as sql

# Patch from http://elixir.ematia.de/trac/wiki/Recipes/GetByOrAddPattern
def get_by_or_init(cls, if_new_set={}, **params):
  """Call get_by; if no object is returned, initialize an
  object with the same parameters.  If a new object was
  created, set any initial values."""
  
  result = cls.get_by(**params)
  if not result:
    result = cls(**params)
    result.set(**if_new_set)
  return result

Entity.get_by_or_init = classmethod(get_by_or_init)

class Feed(Entity):
  htmlUrl     = Field(Text)
  xmlUrl      = Field(Text)
  title       = Field(Text)
  text        = Field(Text)
  description = Field(Text)
  children    = OneToMany('Feed')
  parent      = ManyToOne('Feed')
  posts       = OneToMany('Post')
  lastUpdated = Field(DateTime, default=datetime(1970,1,1))

  def __repr__(self):
    c=self.unreadCount()
    if c:
      return self.text+'(%d)'%c
    return self.text

  def prevSibling(self):
    if not self.parent: return None
    sibs=self.parent.children
    ind=sibs.index(self)
    if ind==0: return None
    else:
      return sibs[ind-1]

  def nextSibling(self):
    if not self.parent: return None
    sibs=self.parent.children
    ind=sibs.index(self)+1
    if ind >= len(sibs):
      return None
    return sibs[ind]

  def nextFeed(self):
    # First see if we have children
    if len(self.children):
      return self.children[0]
    # Then search for a sibling below this one
    sib=self.nextSibling()
    if sib:
      return sib
    else:
      # Go to next uncle/greatuncle/whatever
      parent=self.parent
      while parent:
        nextSib=parent.nextSibling()
        if nextSib: return nextSib.nextFeed()
        parent=parent.parent
    return None

  def nextUnreadFeed(self):
    # First see if we have children with unread articles
    if len(self.children):
      for child in self.children:
        if child.unreadCount():
          return child
    # Then search for a sibling with unread items below this one
    sibs=self.parent.children
    for sib in sibs[sibs.index(self)+1:]:
      if sib.unreadCount():
        return sib
    else:
      # Go to next uncle/greatuncle/whatever
      parent=self.parent
      while parent:
        nextSib=parent.nextSibling()
        if nextSib: return nextSib.nextUnreadFeed()
        parent=parent.parent
    # There is nothing below, so go to the top and try again
    return root_feed.nextUnreadFeed()

  def unreadCount(self):
    if self.children:
      return sum([ f.unreadCount() for f in self.children])
    else:
      return Post.query.filter(Post.feed==self).filter(Post.unread==True).count()
    
  def update(self):
    statusQueue.put(u"Updating: "+ self.title)
    if not self.xmlUrl: # Not a real feed
      return
    d=fp.parse(self.xmlUrl)
    posts=[]
    for post in d['entries']:
      try:
        # Date can be one of several fields
        if 'created_parsed' in post:
          dkey='created_parsed'
        elif 'published_parsed' in post:
          dkey='published_parsed'
        elif 'modified_parsed' in post:
          dkey='modified_parsed'
        else:
          dkey=None
        if dkey and post[dkey]:
          date=datetime.fromtimestamp(time.mktime(post[dkey]))
        else:
          date=datetime.now()
        
        # So can the "unique ID for this entry"
        if 'id' in post:
          idkey='id'
        elif 'link' in post:
          idkey='link'
       
        # So can the content
       
        if 'content' in post:
          content='<hr>'.join([ c.value for c in post['content']])
        elif 'summary' in post:
          content=post['summary']
        elif 'value' in post:
          content=post['value']
         
        # Author if available, else None
        author=''
        # First, we may have author_detail, which is the nicer one
        if 'author_detail' in post:
          ad=post['author_detail']
          author=detailToAuthor(ad)
        # Or maybe just an author
        elif 'author' in post:
          author=post['author']
          
        # But we may have a list of contributors
        if 'contributors' in post:
          # Which may have the same detail as the author's
          author+=' - '.join([ detailToAuthor(contrib) for contrib in post[contributors]])
        if not author:
          #FIXME: how about using the feed's author, or something like that
          author=None
          
        # The link should be simple ;-)
        if 'link' in post:
          link=post['link']
        else:
            link=None
        # FIXME: if I use date to check here, I get duplicates on posts where I use
        # artificial date because it's not in the feed's entry.
        # If I don't I don't re-get updated posts.
        p = Post.get_by(feed=self, title=post['title'],post_id=post[idkey])
        if not p:
          p=Post(feed=self, date=date, title=post['title'], 
                 post_id=post[idkey], content=content, 
                 author=author, link=link)
        posts.append(p)
      except KeyError:
        print post
    self.lastUpdated=datetime.now()
    session.flush()
    
class Post(Entity):
  feed        = ManyToOne('Feed')
  title       = Field(Text)
  post_id     = Field(Text)
  content     = Field(Text)
  date        = Field(DateTime)
  unread      = Field(Boolean, default=True)
  author      = Field(Text)
  link        = Field(Text)

  def nextUnreadPost(self):
    '''Returns next unread post in this feed or None'''
    # FIXME: think about sorting issues
    post=Post.query.filter(Post.feed==self.feed).filter(Post.unread==True).\
          filter(Post.date <= self.date).filter(Post.id<>self.id).\
          order_by(sql.desc(Post.date)).first()
    if post:
      return post
    return None
    
  def __repr__(self):
    return unicode(self.title)

root_feed=None

def initDB():
  global root_feed
  # This is just temporary
  metadata.bind = "sqlite:///urssus.sqlite"
  # metadata.bind.echo = True
  setup_all()
  if not os.path.exists("urssus.sqlite"):
    create_all()
  root_feed=Feed.get_by_or_init(parent=None)

# UI Classes
from PyQt4 import QtGui, QtCore, QtWebKit
from Ui_main import Ui_MainWindow
from Ui_about import Ui_Dialog as UI_AboutDialog
from Ui_filterwidget import Ui_Form as UI_FilterWidget
from Ui_searchwidget import Ui_Form as UI_SearchWidget

class FilterWidget(QtGui.QWidget):
  def __init__(self):
    QtGui.QWidget.__init__(self)
    # Set up the UI from designer
    self.ui=UI_FilterWidget()
    self.ui.setupUi(self)
    
class SearchWidget(QtGui.QWidget):
  def __init__(self):
    QtGui.QWidget.__init__(self)
    # Set up the UI from designer
    self.ui=UI_SearchWidget()
    self.ui.setupUi(self)

class AboutDialog(QtGui.QDialog):
  def __init__(self):
    QtGui.QDialog.__init__(self)
    # Set up the UI from designer
    self.ui=UI_AboutDialog()
    self.ui.setupUi(self)

class MainWindow(QtGui.QMainWindow):
  def __init__(self):
    QtGui.QMainWindow.__init__(self)
  
    # Set up the UI from designer
    self.ui=Ui_MainWindow()
    self.ui.setupUi(self)
    
    # Use custom delegate to paint feed and post items
    self.ui.feeds.setItemDelegate(FeedDelegate(self))
    self.ui.posts.setItemDelegate(PostDelegate(self))
    
    # Article filter fields
    self.filterWidget=FilterWidget()
    self.ui.filterBar.addWidget(self.filterWidget)
    QtCore.QObject.connect(self.filterWidget.ui.filter, QtCore.SIGNAL("returnPressed()"), self.filterPosts)
    QtCore.QObject.connect(self.filterWidget.ui.clear, QtCore.SIGNAL("clicked()"), self.unFilterPosts)
    
    # Search widget
    self.searchWidget=SearchWidget()
    self.searchWidget.hide()
    self.ui.splitter.addWidget(self.searchWidget)
    QtCore.QObject.connect(self.searchWidget.ui.next, QtCore.SIGNAL("clicked()"), self.findText)
    QtCore.QObject.connect(self.searchWidget.ui.previous, QtCore.SIGNAL("clicked()"), self.findTextReverse)
    
    
    # Set some properties of the Web view
    page=self.ui.view.page()
    page.setLinkDelegationPolicy(page.DelegateAllLinks)
    self.ui.view.setFocus(QtCore.Qt.TabFocusReason)

    
    # Fill with feed data
    self.initTree()
    
    # Timer to trigger status bar updates
    self.statusTimer=QtCore.QTimer()
    self.statusTimer.setSingleShot(True)
    QtCore.QObject.connect(self.statusTimer, QtCore.SIGNAL("timeout()"), self.updateStatusBar)
    self.statusTimer.start(0)
    
    # Timer to mark feeds as busy/updated/whatever
    self.feedStatusTimer=QtCore.QTimer()
    self.feedStatusTimer.setSingleShot(True)
    QtCore.QObject.connect(self.feedStatusTimer, QtCore.SIGNAL("timeout()"), self.updateFeedStatus)
    self.feedStatusTimer.start(0)
    self.updatesCounter=0
    
    # Internal indexes
    self.posts=[]
    self.currentFeed=None

  def on_actionFind_triggered(self, i=None):
    if i==None: return
    self.searchWidget.show()
    self.searchWidget.ui.text.setFocus(QtCore.Qt.TabFocusReason)

  def on_actionFind_Again_triggered(self, i=None):
    if i==None: return
    self.findText()

  def findText(self):
    # FIXME: handle "Match Case"
    text=unicode(self.searchWidget.ui.text.text())
    self.ui.view.findText(text)

  def findTextReverse(self):
    # FIXME: handle "Match Case"
    text=unicode(self.searchWidget.ui.text.text())
    self.ui.view.findText(text, QtWebKit.QWebPage.FindBackward)

  def unFilterPosts(self):
    self.open_feed(self.ui.feeds.currentIndex())

  def filterPosts(self):
    self.open_feed(self.ui.feeds.currentIndex(), filter=self.filterWidget.ui.filter.text())
    
  def on_view_linkClicked(self, url):
    QtGui.QDesktopServices.openUrl(url)
        
  def on_actionStatus_Bar_triggered(self, i=None):
    if i==None: return
    if self.ui.actionStatus_Bar.isChecked():
      self.statusBar().show()
    else:
      self.statusBar().hide()

  def on_actionAbout_uRSSus_triggered(self, i=None):
    if i==None: return
    AboutDialog().exec_()
    
  def updateFeedStatus(self):
    while not feedStatusQueue.empty():
      [action, id] = feedStatusQueue.get()
      if not id in self.feedItems:
        # This shouldn't happen, it means there is a 
        # feed that is not in the tree
        print "id %s not in the tree"%id
        print Feed.get_by(id=id)
        sys.exit(1)
      item=self.feedItems[id]

      #FIXME: use the palette to find the correct colors
      if action==0: # Mark as updating
        item.setForeground(QtGui.QBrush(QtGui.QColor("lightgrey")))
        self.updatesCounter+=1
      if action==1: # Mark as finished updating
        item.setForeground(QtGui.QBrush(QtGui.QColor("black")))
        self.updatesCounter-=1
        
      item.setText(unicode(item.feed))
      if self.updatesCounter>0:
        self.ui.actionAbort_Fetches.setEnabled(True)
      else:
        self.ui.actionAbort_Fetches.setEnabled(False)

    self.feedStatusTimer.start(1000)

  def updateStatusBar(self):
    if not statusQueue.empty():
      msg=statusQueue.get()
      self.statusBar().showMessage(msg)
    else:
      self.statusBar().showMessage("")      
    if statusQueue.empty():
      self.statusTimer.start(1000)
    else:
      self.statusTimer.start(100)

  def initTree(self):
    # Initialize the tree from the Feeds
    self.model=QtGui.QStandardItemModel()
    self.ui.feeds.setModel(self.model)
    self.feedItems={}
    
    # Internal function
    def addSubTree(parent, node):
      nn=QtGui.QStandardItem(unicode(node))
      nn.setToolTip(unicode(node))
      parent.appendRow(nn)
      nn.feed=node
      self.feedItems[node.id]=nn
      if node.children:
        nn.setIcon(QtGui.QIcon(":/folder.svg"))
        for child in node.children:
          addSubTree(nn, child)
      else:
        nn.setIcon(QtGui.QIcon(":/urssus.svg"))
      return nn
          
    iroot=self.model.invisibleRootItem()
    iroot.feed=root_feed
    for root in root_feed.children:
      addSubTree(iroot, root)
      
    self.ui.feeds.expandAll()
    
  def on_view_loadProgress(self, p):
    self.statusBar().showMessage("Page loaded %d%%"%p)

  def on_feeds_clicked(self, index, filter=None):
    item=self.model.itemFromIndex(index)
    if not item: return
    self.open_feed(index, filter)
    self.ui.view.setHtml(tmplLookup.get_template('feed.tmpl').render_unicode(feed=item.feed))
    if item.feed.title:
      self.setWindowTitle("%s - uRSSus"%item.feed.title)
    if item.feed.text:
      self.setWindowTitle("%s - uRSSus"%item.feed.text)
    else:
      self.setWindowTitle("uRSSus")

  def open_feed(self, index, filter=None):
    item=self.model.itemFromIndex(index)
    if not item: return
    self.ui.feeds.setCurrentIndex(index)
    feed=item.feed
    self.currentFeed=feed
    self.postItems={}
    self.posts=[]
    if not filter:
      self.posts=Post.query.filter(Post.feed==feed).order_by(sql.desc("date"))
    else:
      self.posts=Post.query.filter(Post.feed==feed).filter(sql.or_(Post.title.like('%%%s%%'%filter), Post.content.like('%%%s%%'%filter))).order_by(sql.desc("date"))
    self.ui.posts.__model=QtGui.QStandardItemModel()
    for post in self.posts:
      item=QtGui.QStandardItem('%s - %s'%(decodeString(post.title), post.date))
      item.post=post
      self.ui.posts.__model.appendRow(item)
      self.postItems[post.id]=item
    self.ui.posts.setModel(self.ui.posts.__model)

  def updateFeedItem(self, feed):
    self.feedItems[post.feed.id].setText(unicode(post.feed))

  def on_posts_clicked(self, index=None, item=None):
    if item: post=item.post
    else: post=self.ui.posts.model().itemFromIndex(index).post
    post.unread=False
    session.flush()
    self.updateFeedItem(post.feed)
    self.ui.view.setHtml(tmplLookup.get_template('post.tmpl').render_unicode(post=post))

  def on_actionImport_Feeds_triggered(self, i=None):
    if i==None: return
    fname = unicode(QtGui.QFileDialog.getOpenFileName(self, "Open OPML file", os.getcwd(), 
                                              "OPML files (*.opml *.xml)"))
    if fname:
      importOPML(fname)
      self.initTree()
      
  def on_actionQuit_triggered(self, i=None):
    if i==None: return
    QtGui.QApplication.instance().quit()

  def on_actionMark_Feed_as_Read_triggered(self, i=None):
    if i==None: return
    item=self.model.itemFromIndex(self.ui.feeds.currentIndex())
    if item and item.feed:
      for post in item.feed.posts:
        post.unread=False
      session.flush()
      self.updateFeedItem(item.feed)

  def on_actionFetch_Feed_triggered(self, i=None):
    if i==None: return
    # Start an immediate update for the current feed
    item=self.model.itemFromIndex(self.ui.feeds.currentIndex())
    if item and item.feed:
      # FIXME: move to out-of-process
      feedStatusQueue.put([0, item.feed.id])
      item.feed.update()
      feedStatusQueue.put([1, item.feed.id])
      self.open_feed(self.ui.feeds.currentIndex())

  def on_actionFetch_All_Feeds_triggered(self, i=None):
    if i==None: return
    global processes
    # Start an immediate update for all feeds
    statusQueue.put("fetching all feeds")
    p = processing.Process(target=feedUpdater, args=(True, ))
    p.setDaemon(True)
    p.start()
    processes.append(p)
    
  def on_actionAbort_Fetches_triggered(self, i=None):
    if i==None: return
    global processes, statusQueue, feedStatusQueue
    statusQueue.put("Aborting all fetches")
    # stop all processes and restart the background timed fetcher
    for proc in processes:
      proc.terminate()
    processes=[]
    
    # Mark all feeds as not updating
    for id in self.feedItems:
      feedStatusQueue.put([1, id])
    self.updateFeedStatus()
    self.updatesCounter=0
    
    # Since we terminate forcefully, the contents of the
    # queues are probably corrupted. So throw them away.
    statusQueue=processing.Queue()
    feedStatusQueue=processing.Queue()
    
    p = processing.Process(target=feedUpdater)
    p.setDaemon(True)
    p.start()
    processes.append(p)
    
  def on_actionNext_Unread_Article_triggered(self, i=None):
    if i==None: return
    print "Next Unread"
    if Post.query.filter(Post.unread==True).count()==0:
      return #No unread articles, so don't bother
    curIndex=self.ui.posts.currentIndex()
    curItem=self.ui.posts.model().itemFromIndex(curIndex)
    if curItem:
      nextPost=curItem.post.nextUnreadPost()
      if nextPost:
        print "Jumping to ", nextPost
        nextIndex=self.ui.posts.model().indexFromItem(self.postItems[nextPost.id])
        self.ui.posts.setCurrentIndex(nextIndex)
        self.on_posts_clicked(index=nextIndex)
      else:
        nextFeed=curItem.post.feed.nextUnreadFeed()
        if not nextFeed: # Go to first unread feed
          nextFeed=root_feed.nextUnreadFeed()
        if nextFeed:
          self.open_feed(self.model.indexFromItem(self.feedItems[nextFeed.id]))

    else:
      # There is no article selected, so if there are unread articles,
      # go to first unread.
      # If there aren't, go to next unread feed
      for nextPost in self.posts:
        if nextPost.unread:
          nextIndex=self.ui.posts.model().indexFromItem(self.postItems[nextPost.id])
          self.ui.posts.setCurrentIndex(nextIndex)
          self.on_posts_clicked(index=nextIndex)
          break
      else: # No unreads or no posts
        nextFeed=self.currentFeed.nextUnreadFeed()
        if not nextFeed:
          nextFeed=root_feed.nextUnreadFeed()
        if nextFeed:
          self.open_feed(self.model.indexFromItem(self.feedItems[nextFeed.id]))

  def on_actionNext_Article_triggered(self, i=None, do_open=True):
    if i==None: return
    print "Next"
    # First see if we have a next item here
    curIndex=self.ui.posts.currentIndex()
    if curIndex.isValid():
      nextIndex=curIndex.sibling(curIndex.row()+1, 0)
      if nextIndex.isValid():
        self.ui.posts.setCurrentIndex(nextIndex)
      else: # This was the last item here, need to go somewhere else
        print "At last post"
        self.on_actionNext_Feed_triggered(True)
    else: # At no post in particular
      # Are there any item in this model?
      if self.ui.posts.model() and self.ui.posts.model().rowCount()>0:
        # Then go to the first one
        self.ui.posts.setCurrentIndex(self.ui.posts.model().index(0, 0))
      else: # No items here, we need to go to the next feed
        print "No posts"
        self.on_actionNext_Feed_triggered(True)
    it=self.ui.posts.model().itemFromIndex(self.ui.posts.currentIndex())
    if do_open:
      self.on_posts_clicked(index=self.ui.posts.currentIndex())

  def on_actionPrevious_Unread_Article_triggered(self, i=None):
    if i==None: return
    print "Previous Unread"
    if Post.query.filter(Post.unread==True).count()==0:
      return #No unread articles, so don't bother
    # Go to next article
    while True:
      self.on_actionPrevious_Article_triggered(True, do_open=False)
      curIndex=self.ui.posts.currentIndex()
      curItem=self.ui.posts.model().itemFromIndex(curIndex)
      if (curItem and curItem.post.unread):
        break
      if not (self.ui.feeds.currentIndex().parent().isValid() and self.ui.feeds.currentIndex().isValid()):
        break
    self.on_posts_clicked(index=self.ui.posts.currentIndex())

  def on_actionPrevious_Article_triggered(self, i=None, do_open=True):
    if i==None: return
    print "Previous"
    # First see if we have a previous item here
    curIndex=self.ui.posts.currentIndex()
    if curIndex.isValid(): 
      if curIndex.row()>0:
        nextIndex=curIndex.sibling(curIndex.row()-1, 0)
        self.ui.posts.setCurrentIndex(nextIndex)
      else: # This was the first item here, need to go to previous feed
        print "At first post"
        self.on_actionPrevious_Feed_triggered(True)
    else: # At no post in particular
      # Are there any item in this model?
      if self.ui.posts.model() and self.ui.posts.model().rowCount()>0:
        # Then go to the last one
        i=self.ui.posts.model().index(self.ui.posts.model().rowCount()-1, 0)
        self.ui.posts.setCurrentIndex(i)
      else: # No items here, we need to go to the previous feed
        print "No posts"
        self.on_actionPrevious_Feed_triggered(True)
    it=self.ui.posts.model().itemFromIndex(self.ui.posts.currentIndex())
    if do_open:
      self.on_posts_clicked(index=self.ui.posts.currentIndex())

  def on_actionNext_Unread_Feed_triggered(self, i=None):
    if i==None: return
    print "Next unread feed"
    if Post.query.filter(Post.unread==True).count()==0:
      return #No unread articles, so don't bother
    if self.currentFeed:
      nextFeed=self.currentFeed.nextUnreadFeed()
    else:
      nextFeed=root_feed.nextUnreadFeed()
    if nextFeed:
      self.open_feed(self.ui.feeds.model().indexFromItem(self.feedItems[nextFeed.id]))

  def on_actionNext_Feed_triggered(self, i=None):
    if i==None: return
    print "Next Feed"
    if self.currentFeed:
      nextFeed=self.currentFeed.nextFeed()
    else:
      nextFeed=root_feed.nextFeed()
    if nextFeed:
      self.open_feed(self.ui.feeds.model().indexFromItem(self.feedItems[nextFeed.id]))

  def on_actionPrevious_Feed_triggered(self, i=None):
    if i==None: return
    print "Previous Feed"
    nextIndex=None
    # First see if we are on a specific feed
    curIndex=self.ui.feeds.currentIndex()
    if curIndex.isValid():
      # If there is a previous sibling, go there
      if curIndex.row()>0:
        nextIndex=curIndex.sibling(curIndex.row()-1, 0)
        # And then dig to the last leaf
        while self.ui.feeds.model().hasChildren(nextIndex):
          nextIndex=nextIndex.child(self.ui.feeds.model().rowCount(nextIndex)-1, 0)
      # No previous sibling, go to the parent
      else:
          nextIndex=curIndex.parent()
        
    else: # Just go to the first feed there is
      i=self.ui.feeds.model().index(0, 0) # This one always exists, unless you have no feeds, in which case, who cares?
      it=self.model.itemFromIndex(i)
      # dig until there is something
      while (it.feed==None or it.feed.xmlUrl==None) and self.ui.feeds.model().hasChildren(i):
        i=self.model.index(0, 0, i)
        it=self.model.itemFromIndex(i)
      nextIndex=i

    # And go there
    if nextIndex and nextIndex.isValid():
      self.ui.feeds.setCurrentIndex(nextIndex)
      # If nextIndex is not a real feed, we need to do one more step forward
      it=self.model.itemFromIndex(nextIndex)  
      if it.feed==None or it.feed.xmlUrl==None:
        self.on_actionPrevious_Feed_triggered(True)
      else: # Finally!
        self.open_feed(nextIndex)

  def on_actionPrevious_Unread_Feed_triggered(self, i=None):
    if i==None: return
    if Post.query.filter(Post.unread==True).count()==0:
      return #No unread articles, so don't bother
    # Go to previous feed
    while True:
      self.on_actionPrevious_Feed_triggered(True)
      curIndex=self.ui.feeds.currentIndex()
      curItem=self.ui.feeds.model().itemFromIndex(curIndex)
      if curItem and curItem.feed and curItem.feed.unreadCount()<>0:
        break

  def on_actionIncrease_Font_Sizes_triggered(self, i=None):
    if i==None: return
    self.ui.view.setTextSizeMultiplier(self.ui.view.textSizeMultiplier()+.2)
    
  def on_actionDecrease_Font_Sizes_triggered(self, i=None):
    if i==None: return
    self.ui.view.setTextSizeMultiplier(self.ui.view.textSizeMultiplier()-.2)

class FeedDelegate(QtGui.QItemDelegate):
  def __init__(self, parent=None):
    print "Creating FeedDelegate"
    QtGui.QItemDelegate.__init__(self, parent)
    
class PostDelegate(QtGui.QItemDelegate):
  def __init__(self, parent=None):
    print "Creating PostDelegate"
    QtGui.QItemDelegate.__init__(self, parent)
  
def importOPML(fname):
  def importSubTree(parent, node):
    if node.tag<>'outline':
      return # Don't handle
    xu=node.get('xmlUrl')
    if xu:
      # If it's already somewhere, don't duplicate
      f=Feed.get_by(xmlUrl=node.get('xmlUrl'), 
             htmlUrl=node.get('htmlUrl'), 
             )
      if not f:
        f=Feed(xmlUrl=node.get('xmlUrl'), 
             htmlUrl=node.get('htmlUrl'), 
             title=node.get('title'),
             text=node.get('text'), 
             description=node.get('description'), 
             parent=parent
             )
    else: # Let's guess it's a folder
      f=Feed.get_by_or_init(text=node.get('text'), parent=parent)
      for child in node.getchildren():
        importSubTree(f, child)

  from xml.etree import ElementTree
  tree = ElementTree.parse(fname)
  parent=root_feed
  for node in tree.find('//body').getchildren():
    importSubTree(parent, node)
  session.flush()

# The feed updater (runs out-of-process)
def feedUpdater(full=False):
  initDB()
  if full:
      for feed in Feed.query.filter(Feed.xmlUrl<>None):
        feedStatusQueue.put([0, feed.id])
        try: # we can't let this fail or it will stay yellow forever;-)
          feed.update()
        except:
          pass
        feedStatusQueue.put([1, feed.id])
  else:
    while True:
      print "updater loop"
      time.sleep(60)
      now=datetime.now()
      for feed in Feed.query.filter(Feed.xmlUrl<>None):
        if (now-feed.lastUpdated).seconds>1800:
          print "updating because of timeout"
          feedStatusQueue.put([0, feed.id])
          try: # we can't let this fail or it will stay yellow forever;-)
            feed.update()
          except:
            pass
          feedStatusQueue.put([1, feed.id])
      print "---------------------"

from BeautifulSoup import BeautifulStoneSoup 
def decodeString(s):
  '''Decode HTML strings so you don't get &lt; and all those things.'''
  u=unicode(BeautifulStoneSoup(s,convertEntities=BeautifulStoneSoup.HTML_ENTITIES ))
  return u
  
if __name__ == "__main__":
  initDB()
    
  if len(sys.argv)>1:
      # Import a OPML file into the DB so we have some data to work with
      importOPML(sys.argv[1])
  app=QtGui.QApplication(sys.argv)
  window=MainWindow()
  
  # This will start the background fetcher as a side effect
  window.on_actionAbort_Fetches_triggered(True)
  window.show()
  sys.exit(app.exec_())

