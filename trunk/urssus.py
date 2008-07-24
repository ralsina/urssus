# -*- coding: utf-8 -*-

import sys, os, time, urlparse
from urllib import urlopen
from datetime import datetime, timedelta

# Configuration
import config

# Logging
from easylog import critical, error, warning, debug, info, setLogger, DEBUG
setLogger(name='urssus', level=DEBUG)

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
# [2,id,parents] means "refresh the text" (for example if you read an article, 
#                         to update the unread count,parents updates all parents)
# [3,id,count] means "notify on the systray icon that there are new articles here

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
  htmlUrl        = Field(Text)
  xmlUrl         = Field(Text)
  title          = Field(Text)
  text           = Field(Text, default='')
  description    = Field(Text)
  children       = OneToMany('Feed')
  parent         = ManyToOne('Feed')
  posts          = OneToMany('Post')
  lastUpdated    = Field(DateTime, default=datetime(1970,1,1))
  loadFull       = Field(Boolean, default=False)
  # meaning of archiveType:
  # 0 = use default, 1 = keepall, 2 = use limitCount
  # 3 = use limitDays, 4 = no archiving
  archiveType    = Field(Integer, default=0) 
  limitCount     = Field(Integer, default=1000)
  limitDays      = Field(Integer, default=60)

  notify         = Field(Boolean, default=False)
  markRead       = Field(Boolean, default=False)
  icon           = Field(Binary, deferred=True)
  # updateInterval -1 means use the app default, any other value, it's in minutes
  updateInterval = Field(Integer, default=-1)
  curUnread      = -1

  def __repr__(self):
    c=self.unreadCount()
    if c:
      return self.text+'(%d)'%c
    return self.text

  def allPosts(self):
    '''This is used if you want all posts in this feed as well as in its childrens.
    Obviously meant to be used with folders, not regular feeds ;-)
    '''
    if self.xmlUrl: #I'm not a folder
      return []
    info("allposts for feed: %s", self)
    
    # Get posts for all children
    posts=[]
    for child in self.children:
      posts.extend(child.posts)
    return posts
    
  def previousSibling(self):
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

  def lastChild(self):
    '''Goes to the last possible child of this feed (the last child of the last child ....)'''
    if not self.children:
      return self
    else:
      return self.children[-1].lastChild()

  def previousFeed(self):
    # Search for a sibling above this one, then dig
    sib=self.previousSibling()
    if sib:
      return sib.lastChild()
    else:
      # Go to parent
      if self.parent:
        return self.parent
    # We are probably at the root
    return None

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

  def previousUnreadFeed(self):
    # If there are no unread articles, there is no point
    if Post.query.filter(Post.unread==True).count()==0:
      return None
      
    # First see if there is any sibling with unread items above this one
    sibs=self.parent.children
    sibs=sibs[:sibs.index(self)]
    sibs.reverse()
    for sib in sibs:
      if sib.unreadCount():
        return sib
    # Then see if our parent is the answer
    if self.parent and self.parent.unreadCount():
      return self.parent
    elif self.parent:
      # Not him, pass the ball to uncle/gramps/whatever
      return self.parent.previousUnreadFeed()
    # Maybe should go to the *last* feed with unread articles, but it's
    # a corner case
    return None

  def nextUnreadFeed(self):
    # If there are no unread articles, there is no point
    if Post.query.filter(Post.unread==True).count()==0:
      return None
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
      self.curUnread=sum([ f.unreadCount() for f in self.children])
    else:
      if self.curUnread==-1:
        info ("Forcing recount in %s", self.title)
        self.curUnread=Post.query.filter(Post.feed==self).filter(Post.unread==True).count()
    return self.curUnread
      
  def updateFeedData(self):
    print "Updating data for feed: ", unicode(self)
    # assumes this feed has a xmlUrl, fetches any missing data from it
    if not self.xmlUrl: # Nowhere to fetch data from
      return
    info ( "Updating feed data from: %s", self.xmlUrl)
    d=fp.parse(self.xmlUrl)
    if not self.htmlUrl:
      self.htmlUrl=d['feed']['link']
    if not self.title:
      self.title=d['feed']['title']
      self.text=d['feed']['title']
    if not self.description:
      if 'info' in d['feed']:
        self.description=d['feed']['info']
      elif 'description' in d['feed']:
        self.description=d['feed']['description']
    if not self.icon:
      # FIXME: handle 404, 403 whatever errors
      self.icon=urlopen(urlparse.urljoin(self.htmlUrl,'/favicon.ico')).read()
      open('/tmp/icon.ico', 'w').write(self.icon)
    session.flush()

    
  def update(self):
    if not self.xmlUrl: # Not a real feed
      # FIXME: should update all children?
      return
    if self.title:
      statusQueue.put(u"Updating: "+ self.title)
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
        debug( post )
    self.lastUpdated=datetime.now()
    session.flush()
    # Force full recount of unread articles for this and all parents
    f=self
    while f.parent:
      f.curUnread=-1
      f.unreadCount()
      f=f.parent
      
    # Queue a notification if needed
    if posts and self.notify:
      feedStatusQueue.put([3, self.id, len(posts)])
    
class Post(Entity):
  feed        = ManyToOne('Feed')
  title       = Field(Text)
  post_id     = Field(Text)
  content     = Field(Text)
  date        = Field(DateTime)
  unread      = Field(Boolean, default=True)
  important   = Field(Boolean, default=False)
  author      = Field(Text)
  link        = Field(Text)

  def nextUnreadPost(self):
    '''Returns next unread post in this feed or None'''
    # FIXME: think about sorting/filtering issues
    post=Post.query.filter(Post.feed==self.feed).filter(Post.unread==True).\
          filter(Post.date <= self.date).filter(Post.id<>self.id).\
          order_by(sql.desc(Post.date)).first()
    if post:
      return post
    return None

  def nextPost(self):
    '''Returns next post in this feed or None'''
    # FIXME: think about sorting/filtering issues
    post=Post.query.filter(Post.feed==self.feed).\
          filter(Post.date <= self.date).filter(Post.id<>self.id).\
          order_by(sql.desc(Post.date)).first()
    if post:
      return post
    return None

  def previousUnreadPost(self):
    '''Returns previous post in this feed or None'''
    # FIXME: think about sorting/filtering issues
    post=Post.query.filter(Post.feed==self.feed).filter(Post.unread==True).\
          filter(Post.date >= self.date).filter(Post.id<>self.id).\
          order_by(Post.date).first()
    if post:
      return post
    return None
    
  def previousPost(self):
    '''Returns previous post in this feed or None'''
    # FIXME: think about sorting/filtering issues
    post=Post.query.filter(Post.feed==self.feed).\
          filter(Post.date >= self.date).filter(Post.id<>self.id).\
          order_by(Post.date).first()
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
from Ui_feed_properties import Ui_Dialog as UI_FeedPropertiesDialog

class PostModel(QtGui.QStandardItemModel):
  def __init__(self):
    QtGui.QStandardItemModel.__init__(self)
    self.setColumnCount(2)
    self.setHeaderData(0, QtCore.Qt.Horizontal, QtCore.QVariant("Title"))
    self.setHeaderData(1, QtCore.Qt.Horizontal, QtCore.QVariant("Date"))

  def data(self, index, role):
    if not index.isValid():
      return QtCore.QVariant()
      
    if role<>QtCore.Qt.DisplayRole:
      return QtGui.QStandardItemModel.data(self, index, role)
    
    if index.column()==0:
      item=self.itemFromIndex(index)
      v=QtCore.QVariant(item.post.title)
    elif index.column()==1:
      # Tricky!
      ind=self.index(index.row(), 0, index.parent())
      item=self.itemFromIndex(ind)
      v=QtCore.QVariant(str(item.post.date))
    else:
      return QtCore.QVariant()
    return v
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

class TrayIcon(QtGui.QSystemTrayIcon):
  def __init__(self):
    QtGui.QSystemTrayIcon.__init__ (self,QtGui.QIcon(":/urssus.svg"))
 
class FeedProperties(QtGui.QDialog):
  def __init__(self, feed):
    QtGui.QDialog.__init__(self)
    # Set up the UI from designer
    self.ui=UI_FeedPropertiesDialog()
    self.ui.setupUi(self)
    self.ui.tabWidget.setCurrentIndex(0)
    self.feed=feed
    self.loadData()
  
  def loadData(self):
    feed=self.feed
    self.ui.name.setText(feed.text)
    self.ui.url.setText(feed.xmlUrl)
    self.ui.notify.setChecked(feed.notify)
    if feed.updateInterval==-1: # Use default
      self.ui.updatePeriod.setEnabled(False)
      self.ui.updateUnit.setEnabled(False)
      self.ui.customUpdate.setChecked(False)
    else:
      pass # Implement
    if feed.archiveType==0: # Use default archiving
      self.ui.useDefault.setChecked(True)
    elif feed.archiveType==1: # Keep all articles
      self.ui.keepAll.setChecked(True)
    elif feed.archiveType==2: # Keep a number of articles
      self.ui.limitCount.setChecked(True)
      self.ui.count.setValue(feed.limitCount)
    elif feed.archiveType==3: # Keep for a period of time
      self.ui.limitDays.setChecked(True)
      self.ui.days.setValue(feed.limitDays)
    elif feed.archiveType==4: # Keep nothing
      self.ui.noArchive.setChecked(True)
  
    self.ui.loadFull.setChecked(feed.loadFull)
    self.ui.markRead.setChecked(feed.markRead)
    
  def accept(self):
    feed=self.feed
    feed.text=unicode(self.ui.name.text())
    # FIXME: validate
    feed.xmlUrl=unicode(self.ui.url.text())
    feed.notify=self.ui.notify.isChecked()
    
    if self.ui.customUpdate.isChecked():
      multiplier=[1, 60, 1440, 0][self.ui.updateUnit.currentIndex()]
      feed.updateInterval=self.ui.updatePeriod.value()*multiplier

    session.flush()
    QtGui.QDialog.accept(self)
 
class MainWindow(QtGui.QMainWindow):
  def __init__(self):
    QtGui.QMainWindow.__init__(self)

    # Internal indexes
    self.posts=[]
    self.currentFeed=None
    self.currentPost=None

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
    # TODO: make configurable
    self.showOnlyUnread=False
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

    # Load user preferences
    self.loadPreferences()

    # Tray icon
    self.tray=TrayIcon()
    self.tray.show()
    self.notifiedFeed=None
    QtCore.QObject.connect(self.tray, QtCore.SIGNAL("messageClicked()"), self.notificationClicked)

  def notificationClicked(self):
    if self.notifiedFeed:
      self.open_feed(self.ui.feeds.model().indexFromItem(self.feedItems[self.notifiedFeed.id]))

  def loadPreferences(self):
    
    v=config.getValue('ui', 'showStatus', True)
    self.ui.actionStatus_Bar.setChecked(v)
    self.on_actionStatus_Bar_triggered(v)
    
    v=config.getValue('ui', 'showOnlyUnreadFeeds', False)
    self.ui.actionShow_Only_Unread_Feeds.setChecked(v)
    self.on_actionShow_Only_Unread_Feeds_triggered(v)

  def on_actionDelete_Article_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    index=self.ui.posts.currentIndex()
    if index.isValid():         
      curPost=self.ui.posts.model().itemFromIndex(index).post
    info ("Deleting post: %s", curPost)
    curPost.delete()
    session.flush()
    self.open_feed(self.ui.feeds.currentIndex())

  def on_actionMark_as_Read_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    index=self.ui.posts.currentIndex()
    if index.isValid():         
      curPost=self.ui.posts.model().itemFromIndex(index).post
    if post.unread:
      info ("Marking as read post: %s", curPost)
      curPost.unread=False
      curPost.feed.curUnread-=1 
      session.flush()
      self.updatePostItem(curPost)

  def on_actionMark_as_Unread_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    index=self.ui.posts.currentIndex()
    if index.isValid():         
      curPost=self.ui.posts.model().itemFromIndex(index).post
    if not post.unread:
      info ("Marking as unread post: %s", curPost)
      curPost.unread=True
      curPost.feed.curUnread+=1
      session.flush()
      self.updatePostItem(curPost)

  def on_actionMark_as_Important_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    index=self.ui.posts.currentIndex()
    if index.isValid():         
      curPost=self.ui.posts.model().itemFromIndex(index).post
    info ("Marking as important post: %s", curPost)
    curPost.important=True
    session.flush()
    self.updatePostItem(curPost)

  def on_actionRemove_Important_Mark_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    index=self.ui.posts.currentIndex()
    if index.isValid():         
      curPost=self.ui.posts.model().itemFromIndex(index).post
    info ("Marking as not important post: %s", curPost)
    curPost.important=False
    session.flush()
    self.updatePostItem(curPost)


  def on_posts_customContextMenuRequested(self, pos=None):
    # FIXME: handle selections
    if pos==None: return
    item=self.ui.posts.model().itemFromIndex(self.ui.posts.currentIndex())
    if item and item.post:
      menu=QtGui.QMenu()
      menu.addAction(self.ui.actionOpen_in_Browser)
      menu.addSeparator()
      if item.post.important:
        menu.addAction(self.ui.actionMark_as_Important)
      else:
        menu.addAction(self.ui.actionRemove_Important_Mark)
      if item.post.unread:
        menu.addAction(self.ui.actionMark_as_Read)
      else:
        menu.addAction(self.ui.actionMark_as_Unread)
      menu.addAction(self.ui.actionDelete_Article)
      menu.exec_(QtGui.QCursor.pos())

  def on_feeds_customContextMenuRequested(self, pos=None):
    if pos==None: return
    
    item=self.model.itemFromIndex(self.ui.feeds.currentIndex())
    if item and item.feed:
      menu=QtGui.QMenu()
      menu.addAction(self.ui.actionMark_Feed_as_Read)
      menu.addSeparator()
      menu.addAction(self.ui.actionFetch_Feed)
      menu.addSeparator()
      menu.addAction(self.ui.actionOpen_Homepage)
      menu.addSeparator()
      menu.addAction(self.ui.actionEdit_Feed)
      menu.addAction(self.ui.actionDelete_Feed)
      menu.exec_(QtGui.QCursor.pos())

  def on_actionEdit_Feed_triggered(self, i=None):
    if i==None: return
    index=self.ui.feeds.currentIndex()
    if index.isValid():         
      curFeed=self.ui.feeds.model().itemFromIndex(index).feed
    info ("Editing feed: %s", curFeed)

    editDlg=FeedProperties(curFeed)
    if editDlg.exec_():
      # update feed item
      self.updateFeedItem(curFeed)

  def on_actionAdd_Feed_triggered(self, i=None):
    if i==None: return
    # Ask for feed URL
    [url, ok]=QtGui.QInputDialog.getText(self, "Add Feed - uRSSus", "&Feed URL:")
    if ok:
      url=unicode(url)
      # Use Mark pilgrim / Aaron Swartz's RSS finder module
      # FIXME: make this non-blocking somehow
      import feedfinder
      feed=feedfinder.feed(url)
      if not feed:
        QtGui.QMessageBox.critical(self, "Error - uRSSus", "Can't find a feed wit URL: %s"%url)
        return
      info ("Found feed: %s", feed)
      if Feed.get_by(xmlUrl=feed):
        # Already subscribed
        QtGui.QMessageBox.critical(self, "Error - uRSSus", "You are already subscribed")
        return
      newFeed=Feed(xmlUrl=feed)
      newFeed.updateFeedData()
      
      # Figure out the insertion point
      index=self.ui.feeds.currentIndex()
      if index.isValid():         
        curFeed=self.ui.feeds.model().itemFromIndex(index).feed
      else:
        curFeed=root_feed
      # if curFeed is a feed, add as sibling
      if curFeed.xmlUrl:
        newFeed.parent=curFeed.parent
      # if curFeed is a folder, add as child
      else:
        newFeed.parent=curFeed
      session.flush()
      self.initTree()
      self.ui.feeds.setCurrentIndex(self.ui.feeds.model().indexFromItem(self.feedItems[newFeed.id]))
      # FIXME: open feed options dialog

  def on_actionNew_Folder_triggered(self, i=None):
    if i==None: return
    # Ask for folder name
    [name, ok]=QtGui.QInputDialog.getText(self, "Add Folder - uRSSus", "&Folder name:")
    if ok:
      newFolder=Feed(text=unicode(name))
      # Figure out the insertion point
      index=self.ui.feeds.currentIndex()
      if index.isValid():         
        curFeed=self.itemFromIndex(index).feed
      else:
        curFeed=root_feed
      # if curFeed is a feed, add as sibling
      if curFeed.xmlUrl:
        newFolder.parent=curFeed.parent
      # if curFeed is a folder, add as child
      else:
        newFolder.parent=curFeed
      session.flush()
      self.initTree()
      self.ui.feeds.setCurrentIndex(self.ui.feeds.model().indexFromItem(self.feedItems[newFolder.id]))

  def on_actionShow_Only_Unread_Feeds_triggered(self, checked=None):
    if checked==None: return
    info ("Show only unread: %d", checked)
    self.showOnlyUnread=checked
    for feed in Feed.query().all():
      self.updateFeedItem(feed)
    config.setValue('ui', 'showOnlyUnreadFeeds', checked)
  
  def on_actionFind_triggered(self, i=None):
    if i==None: return
    self.searchWidget.show()
    self.searchWidget.ui.text.setFocus(QtCore.Qt.TabFocusReason)

  def on_actionFind_Again_triggered(self, i=None):
    if i==None: return
    self.findText()

  def findText(self):
    text=unicode(self.searchWidget.ui.text.text())
    if self.searchWidget.ui.matchCase.isChecked():
      self.ui.view.findText(text, QtWebKit.QWebPage.FindCaseSensitively)
    else:  
      self.ui.view.findText(text)

  def findTextReverse(self):
    text=unicode(self.searchWidget.ui.text.text())
    if self.searchWidget.ui.matchCase.isChecked():
      self.ui.view.findText(text, QtWebKit.QWebPage.FindBackward | QtWebKit.QWebPage.FindCaseSensitively)
    else:  
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
    config.setValue('ui', 'showStatus', self.ui.actionStatus_Bar.isChecked())

  def on_actionAbout_uRSSus_triggered(self, i=None):
    if i==None: return
    AboutDialog().exec_()
    
  def updateFeedStatus(self):
    while not feedStatusQueue.empty():
      data=feedStatusQueue.get()
      [action, id] = data[:2]
      if not id in self.feedItems:
        # This shouldn't happen, it means there is a 
        # feed that is not in the tree
        error( "id %s not in the tree", id)
        sys.exit(1)
      feed=Feed.get_by(id=id)
      if action==0: # Mark as updating
        self.updateFeedItem(feed, updating=True)
        self.updatesCounter+=1
      elif action==1: # Mark as finished updating
        self.updateFeedItem(feed, updating=False, parents=True)
        self.updatesCounter-=1
      elif action==2: # Just update it
        self.updateFeedItem(feed, data[2])
      elif action==3: # Systray notification
        self.notifiedFeed=feed
        self.tray.showMessage("New Articles", "%d new articles in %s"%(data[2], feed.text) )
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
      self.updateFeedItem(node)
      if node.xmlUrl:
        nn.setIcon(QtGui.QIcon(":/urssus.svg"))
      else:
        nn.setIcon(QtGui.QIcon(":/folder.svg"))
        for child in node.children:
          addSubTree(nn, child)
      return nn
          
    iroot=self.model.invisibleRootItem()
    iroot.feed=root_feed
    self.feedItems[root_feed.id]=iroot
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

  def open_feed(self, index, filter=None):
    item=self.model.itemFromIndex(index)
    if not item: return
    self.ui.feeds.setCurrentIndex(index)
    feed=item.feed
    self.currentFeed=feed
    self.postItems={}
    self.posts=[]
    self.currentPost=None

    # Update window title
    if feed.title:
      self.setWindowTitle("%s - uRSSus"%item.feed.title)
    elif feed.text:
      self.setWindowTitle("%s - uRSSus"%item.feed.text)
    else:
      self.setWindowTitle("uRSSus")
      
    if feed.xmlUrl: # A regular feed
      if not filter:
        self.posts=Post.query.filter(Post.feed==feed).order_by(sql.desc("date")).all()
      else:
        self.posts=Post.query.filter(Post.feed==feed).filter(sql.or_(Post.title.like('%%%s%%'%filter), Post.content.like('%%%s%%'%filter))).order_by(sql.desc("date")).all()
    else: # A folder
      self.posts=feed.allPosts()
    
    self.ui.posts.__model=PostModel()
    self.ui.posts.setModel(self.ui.posts.__model)
    # Fixes for post list UI
    header=self.ui.posts.header()
    header.setStretchLastSection(False)
    header.setResizeMode(0, QtGui.QHeaderView.Stretch)
    header.setResizeMode(1, QtGui.QHeaderView.Fixed)
    header.resizeSection(1, header.fontMetrics().width(' 8888-88-88 88:88:88 ')+4)
    
    for post in self.posts:
      item=QtGui.QStandardItem('%s - %s'%(decodeString(post.title), post.date))
      item.post=post
      self.ui.posts.__model.appendRow(item)
      self.postItems[post.id]=item
      self.updatePostItem(post)

  def updatePostItem(self, post):
    if not post.id in self.postItems: #post is not being displayed
      return
      
    item=self.postItems[post.id]
    index=self.ui.posts.model().indexFromItem(item)
    item2=self.ui.posts.model().itemFromIndex(self.ui.posts.model().index(index.row(), 1, index.parent()))
    # FIXME: respect the palette
    if post.important:
      item.setForeground(QtGui.QColor("red"))
      item2.setForeground(QtGui.QColor("red"))
    elif post.unread:
      item.setForeground(QtGui.QColor("darkgreen"))
      item2.setForeground(QtGui.QColor("darkgreen"))
    else:
      item.setForeground(QtGui.QColor("black"))
      item2.setForeground(QtGui.QColor("black"))

  def queueUpdateFeedItem(self, feed, parents=False):
    '''Queues a call to updateFeedItem to be done whenever the timer triggers'''
    feedStatusQueue.put([2, feed.id, parents])

  def updateFeedItem(self, feed, parents=False, updating=False):
    item=self.feedItems[feed.id]
    item.setText(unicode(feed))
    # The calls to setRowHidden cause a change in the column's width! Looks like a Qt bug to me.
    if self.showOnlyUnread:
      if feed.unreadCount()==0 and feed<>self.currentFeed: 
        # Hide feeds with no unread items
        self.ui.feeds.setRowHidden(item.row(), self.model.indexFromItem(item.parent()), True)
      else:
        self.ui.feeds.setRowHidden(item.row(), self.model.indexFromItem(item.parent()), False)
    else:
      if self.ui.feeds.isRowHidden(item.row(), self.model.indexFromItem(item.parent())):
        self.ui.feeds.setRowHidden(item.row(), self.model.indexFromItem(item.parent()), False)
    if updating:
      item.setForeground(QtGui.QColor("darkgrey"))
    else:
      item.setForeground(QtGui.QColor("black"))
    if parents: # Not by default because it's slow
      # Update all ancestors too, because unread counts and such change
      while feed.parent:
        self.updateFeedItem(feed.parent, True)
        feed=feed.parent

  def on_posts_clicked(self, index=None, item=None):
    if item: post=item.post
    else: post=self.ui.posts.model().itemFromIndex(index).post
    self.currentPost=post
    if post.unread:
      post.unread=False
      post.feed.curUnread-=1
      session.flush()
    self.updateFeedItem(post.feed, parents=True)
    self.updatePostItem(post)
    if post.feed.loadFull and post.link:
      self.ui.view.setUrl(QtCore.QUrl(post.link))
    else:
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
        if post.unread:
          post.unread=False
          post.feed.curUnread-=1
          self.updatePostItem(post)
      session.flush()
      self.updateFeedItem(item.feed, parents=True)

  def on_actionDelete_Feed_triggered(self, i=None):
    if i==None: return
    index=self.ui.feeds.currentIndex()
    item=self.model.itemFromIndex(index)
    if item and item.feed:
      info( "Deleting %s", item.feed)
      if QtGui.QMessageBox.question(None, "Delete Feed - uRSSus", 
         'Are you sure you want to delete "%s"'%item.feed, 
         QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No ) == QtGui.QMessageBox.Yes:
        item.feed.delete()
        self.ui.feeds.model().removeRow(index.row(), index.parent())
        session.flush()

  def on_actionOpen_Homepage_triggered(self, i=None):
    if i==None: return
    item=self.model.itemFromIndex(self.ui.feeds.currentIndex())
    if item and item.feed and item.feed.htmlUrl:
      info("Opening %s", item.feed.htmlUrl)
      QtGui.QDesktopServices.openUrl(QtCore.QUrl(item.feed.htmlUrl))
    

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
    info( "Next Unread Article")
    if self.currentPost:
      post=self.currentPost
    elif len(self.posts):
      post=self.posts[0]
    else: # No posts in this feed, just go the next unread feed
      self.on_actionNext_Unread_Feed_triggered(True)
    if post.unread: # Quirk, should redo the flow
      nextPost=post
    else:
      nextPost=post.nextUnreadPost()
    if nextPost:
      nextIndex=self.ui.posts.model().indexFromItem(self.postItems[nextPost.id])
      self.ui.posts.setCurrentIndex(nextIndex)
      self.on_posts_clicked(index=nextIndex)
    else:
      # At the end of the feed, go to next unread feed
      self.on_actionNext_Unread_Feed_triggered(True)
      
  def on_actionNext_Article_triggered(self, i=None, do_open=True):
    if i==None: return
    info ("Next Article")
    if self.currentPost:
      nextPost=self.currentPost.nextPost()
    elif len(self.posts):
      nextPost=self.posts[0]
    else: # No posts in this feed, just go the next unread feed
      self.on_actionNext_Feed_triggered(True)
      return
    if nextPost:
      nextIndex=self.ui.posts.model().indexFromItem(self.postItems[nextPost.id])
      self.ui.posts.setCurrentIndex(nextIndex)
      self.on_posts_clicked(index=nextIndex)
    else:
      # At the end of the feed, go to next unread feed
      self.on_actionNext_Feed_triggered(True)

  def on_actionPrevious_Unread_Article_triggered(self, i=None):
    if i==None: return
    info("Previous Unread Article")
    if self.currentPost:
      post=self.currentPost
      previousPost=post.previousUnreadPost()
    elif self.posts: # Not on a specific post, go to the last unread article
      previousPost=self.posts[-1]
      if not previousPost.unread:
        previousPost=previousPost.previousUnreadPost()
    else:
      previousPost=None
    if previousPost:
      nextIndex=self.ui.posts.model().indexFromItem(self.postItems[previousPost.id])
      self.ui.posts.setCurrentIndex(nextIndex)
      self.on_posts_clicked(index=nextIndex)
    else:
      # At the beginning of the feed, go to previous feed
      self.on_actionPrevious_Unread_Feed_triggered(True)

  def on_actionPrevious_Article_triggered(self, i=None, do_open=True):
    if i==None: return
    info ("Previous Article")
    if self.currentPost:
      post=self.currentPost
      previousPost=post.previousPost()
    elif self.posts: # Not on a specific post, go to the last article
      previousPost=posts[-1]
    else:
      previousPost=None
    if previousPost:
      nextIndex=self.ui.posts.model().indexFromItem(self.postItems[previousPost.id])
      self.ui.posts.setCurrentIndex(nextIndex)
      self.on_posts_clicked(index=nextIndex)
    else:
      # At the beginning of the feed, go to previous feed
      self.on_actionPrevious_Feed_triggered(True)

  def on_actionNext_Unread_Feed_triggered(self, i=None):
    if i==None: return
    info("Next unread feed")
    if self.currentFeed:
      nextFeed=self.currentFeed.nextUnreadFeed()
    else:
      nextFeed=root_feed.nextUnreadFeed()
    if nextFeed:
      self.open_feed(self.ui.feeds.model().indexFromItem(self.feedItems[nextFeed.id]))

  def on_actionNext_Feed_triggered(self, i=None):
    if i==None: return
    info("Next Feed")
    if self.currentFeed:
      nextFeed=self.currentFeed.nextFeed()
    else:
      nextFeed=root_feed.nextFeed()
    if nextFeed:
      self.open_feed(self.ui.feeds.model().indexFromItem(self.feedItems[nextFeed.id]))

  def on_actionPrevious_Feed_triggered(self, i=None):
    if i==None: return
    info("Previous Feed")
    if self.currentFeed:
      prevFeed=self.currentFeed.previousFeed()
      if prevFeed and prevFeed<>root_feed: # The root feed has no UI
        self.open_feed(self.ui.feeds.model().indexFromItem(self.feedItems[prevFeed.id]))
    # No current feed, so what's the meaning of "previous feed"?


  def on_actionPrevious_Unread_Feed_triggered(self, i=None):
    if i==None: return
    if self.currentFeed:
      prevFeed=self.currentFeed.previousUnreadFeed()
      if prevFeed and prevFeed<>root_feed: # The root feed has no UI
        self.open_feed(self.ui.feeds.model().indexFromItem(self.feedItems[prevFeed.id]))
    # No current feed, so what's the meaning of "previous unread feed"?
      
  def on_actionIncrease_Font_Sizes_triggered(self, i=None):
    if i==None: return
    self.ui.view.setTextSizeMultiplier(self.ui.view.textSizeMultiplier()+.2)
    
  def on_actionDecrease_Font_Sizes_triggered(self, i=None):
    if i==None: return
    self.ui.view.setTextSizeMultiplier(self.ui.view.textSizeMultiplier()-.2)

class FeedDelegate(QtGui.QItemDelegate):
  def __init__(self, parent=None):
    info("Creating FeedDelegate")
    QtGui.QItemDelegate.__init__(self, parent)
    
class PostDelegate(QtGui.QItemDelegate):
  def __init__(self, parent=None):
    info("Creating PostDelegate")
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
        # Add any missing stuff (mainly icons, I guess)
        # Kills performance, though
        # f.updateFeedData()
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
        try: # we can't let this fail or it will stay marked forever;-)
          feed.update()
        except:
          pass
        feedStatusQueue.put([1, feed.id])
  else:
    while True:
      info("updater loop")
      time.sleep(60)
      now=datetime.now()
      for feed in Feed.query.filter(Feed.xmlUrl<>None):
        period=1800 # FIXME: make this configurable
        if feed.updateInterval==0: # Update never
          continue
        elif feed.updateInterval<>-1: # not update default
          period=60*feed.updateInterval # convert to seconds
        if (now-feed.lastUpdated).seconds>period:
          info("updating because of timeout")
          feedStatusQueue.put([0, feed.id])
          try: # we can't let this fail or it will stay yellow forever;-)
            feed.update()
          except:
            pass
          feedStatusQueue.put([1, feed.id])

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
  # window.on_actionAbort_Fetches_triggered(True)
  window.show()
  sys.exit(app.exec_())
