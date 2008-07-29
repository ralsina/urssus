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


import sys, os, time, urlparse, tempfile
from urllib import urlopen
from datetime import datetime, timedelta

# Configuration
import config

# Logging
if sys.platform=='win32':
  # easylog and Processing on windows == broken
  def dumb(*a, **kw):
    print a, kw
  critical=dumb
  error=dumb
  warning=dumb
  debug=dumb
  info=dumb 
  setLogger=dumb 
  DEBUG=dumb
else:
  from easylog import critical, error, warning, debug, info, setLogger, DEBUG
  setLogger(name='urssus', level=DEBUG)

# Templates
import tenjin
# The obvious import doesn't work for complicated reasons ;-)
to_str=tenjin.helpers.to_str
escape=tenjin.helpers.escape
templateEngine=tenjin.Engine()
tmplDir=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
cssFile=os.path.join(tmplDir,'style.css')

# FIXME: when deploying need to find a decent way to locate the templates
def renderTemplate(tname, **context):
  context['to_str']=to_str
  context['escape']=escape
  return templateEngine.render(os.path.join(tmplDir,tname), context)

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

# Some feeds put html in titles, which can't be shown in QStandardItems
from html2text import html2text as h2t

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
import sqlalchemy as sql
import elixir as elixir
import migrate as migrate
import database

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

elixir.Entity.get_by_or_init = classmethod(get_by_or_init)

root_feed=None

def initDB():
  global root_feed
  REQUIRED_SCHEMA=1
  # FIXME: show what we are doing on the UI
  if not os.path.exists(database.dbfile): # Just create it
    os.system('urssus_upgrade_db')
  else: # May need to upgrade
    try:
      curVer=migrate.versioning.api.db_version(database.dbUrl, database.repo)
    except:
      curVer=0
    if curVer < REQUIRED_SCHEMA:
      print "UPGRADING from %s to %s"%(curVer, REQUIRED_SCHEMA)
      os.system('urssus_upgrade_db')
    
  elixir.metadata.bind = database.dbUrl
  elixir.setup_all()
  elixir.session.flush()
  root_feed=Feed.get_by_or_init(parent=None)
  elixir.session.flush()
  return True

class Post(elixir.Entity):
  elixir.using_options (tablename='posts')
  feed        = elixir.ManyToOne('Feed')
  title       = elixir.Field(elixir.Text)
  post_id     = elixir.Field(elixir.Text)
  content     = elixir.Field(elixir.Text)
  date        = elixir.Field(elixir.DateTime)
  unread      = elixir.Field(elixir.Boolean, default=True)
  important   = elixir.Field(elixir.Boolean, default=False)
  author      = elixir.Field(elixir.Text)
  link        = elixir.Field(elixir.Text)
  deleted     = elixir.Field(elixir.Boolean, default=False)

  def __repr__(self):
    if '<' in self.title:
      return h2t(self.title).strip()
    return unicode(self.title)

class Feed(elixir.Entity):
  elixir.using_options (tablename='feeds')
  htmlUrl        = elixir.Field(elixir.Text)
  xmlUrl         = elixir.Field(elixir.Text)
  title          = elixir.Field(elixir.Text)
  text           = elixir.Field(elixir.Text, default='')
  description    = elixir.Field(elixir.Text)
  children       = elixir.OneToMany('Feed', inverse='parent')
  parent         = elixir.ManyToOne('Feed')
  posts          = elixir.OneToMany('Post', order_by="-date", inverse='feed')
  lastUpdated    = elixir.Field(elixir.DateTime, default=datetime(1970,1,1))
  loadFull       = elixir.Field(elixir.Boolean, default=False)
  # meaning of archiveType:
  # 0 = use default, 1 = keepall, 2 = use limitCount
  # 3 = use limitDays, 4 = no archiving
  archiveType    = elixir.Field(elixir.Integer, default=0) 
  limitCount     = elixir.Field(elixir.Integer, default=1000)
  limitDays      = elixir.Field(elixir.Integer, default=60)

  notify         = elixir.Field(elixir.Boolean, default=False)
  markRead       = elixir.Field(elixir.Boolean, default=False)
  icon           = elixir.Field(elixir.Binary, deferred=True)
  # updateInterval -1 means use the app default, any other value, it's in minutes
  updateInterval = elixir.Field(elixir.Integer, default=-1)
  curUnread      = -1

  def __repr__(self):
    c=self.unreadCount()
    if c:
      return self.text+'(%d)'%c
    return self.text

  def expire(self, expunge=False):
    '''Delete all posts that are too old'''
    # meaning of archiveType:
    # 0 = use default, 1 = keepall, 2 = use limitCount
    # 3 = use limitDays, 4 = no archiving
    now=datetime.now()
    if self.archiveType==0: # Default archive config
      for post in self.posts:
        if post.important: continue # Don't delete important stuff
        # FIXME: makethis configurable
        if (now-post.date).days>7: # Right now, keep for a week
          post.deleted=True
    elif self.archiveType==1: #keepall
      return
    elif self.archiveType==2: #limitCount
      for post in self.posts[self.limitCount:]:
        if post.important: continue # Don't delete important stuff
        post.deleted=True
    elif self.archiveType==3: #limitDays
      for post in self.posts:
        if post.important: continue # Don't delete important stuff
        if (now-post.date).days>self.limitDays: # Right now, keep for a week
          post.deleted=True
    elif self.archiveType==4: #no archiving
      for post in self.posts:
        if post.important: continue # Don't delete important stuff
        post.deleted=True
        
    elixir.session.flush()
    if expunge:
      # Delete all posts with deleted==True 
      for post in Post.query().filter(Post.feed==self).filter(Post.deleted==True).all():
        post.delete()
      elixir.session.flush()
      
    # Force recount
    self.curUnread=-1
    self.unreadCount()

  def allFeeds(self):
    '''Returns a list of all "real" feeds that have this one as ancestor'''
    if not self.children:
      return [self]
    feeds=[]
    for child in self.children:
      feeds.extend(child.allFeeds())
    return feeds

  def allPostsQuery(self):
    '''Returns a query that should give you all the posts contained in this folder's children
    down to any level. Required for aggregate feeds, I'm afraid'''
    af=self.allFeeds()
    ored=sql.or_(*[Post.feed==f for f in af])
    return Post.query().filter(ored)

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
    if not self.parent: # At root feed
      return self.lastChild().previousUnreadFeed()
    sibs=self.parent.children
    sibs=sibs[:sibs.index(self)]
    sibs.reverse()
    for sib in sibs:
      if sib.unreadCount():
        if sib.xmlUrl:
          return sib
        else:
          return sib.previousUnreadFeed()
    # Then see if our parent is the answer
    if self.parent and self.parent.unreadCount():
      if self.parent.xmlUrl:
        return self.parent
      else:
        return self.parent.lastChild().previousUnreadFeed()
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
          if child.xmlUrl:
            return child
          else: # Skip folders
            return child.nextUnreadFeed()
    # Then search for a sibling with unread items below this one
    sibs=self.parent.children
    for sib in sibs[sibs.index(self)+1:]:
      if sib.unreadCount():
        if sib.xmlUrl:
          return sib
        else:
          return sib.nextUnreadFeed()
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
    elixir.session.flush()

    
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
         
        # Rudimentary NON-html detection
        if not '<' in content:
          content=escape(content).replace('\n\n','<p>')
         
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
          if self.markRead:
            p.unread=False
          posts.append(p)
      except KeyError:
        debug( post )
    self.lastUpdated=datetime.now()
    elixir.session.flush()
      
    # Queue a notification if needed
    if posts and self.notify:
      feedStatusQueue.put([3, self.id, len(posts)])

  def getQuery(self):
    if self.xmlUrl:
      return Post.query.filter(Post.feed==self)
    else:
      return self.allPostsQuery()

  def nextPost(self, post, order, required=None, textFilter=''):
    '''Returns next post in this feed after "post" or None'''
    posts=self.getQuery()
    if required:
      posts=posts.filter(sql.or_(Post.id==post.id, required==True))
    if textFilter:
      posts=posts.filter(sql.or_(Post.id==post.id,Post.title.like('%%%s%%'%textFilter), Post.content.like('%%%s%%'%textFilter)))
    posts=posts.order_by(order).all()
    if posts:
      ind=posts.index(post)
      if ind+1<len(posts):
        return posts[ind+1]
    return None

  def nextUnreadPost(self, post, order, required=None, textFilter=''):
    '''Returns next unread post after "post" in this feed or None'''
    posts=self.getQuery().filter(sql.or_(Post.unread==True, Post.id==post.id))
    if required:
      posts=posts.filter(sql.or_(Post.id==post.id, required==True))
    if textFilter:
      posts=posts.filter(sql.or_(Post.id==post.id,Post.title.like('%%%s%%'%textFilter), Post.content.like('%%%s%%'%textFilter)))
    posts=posts.order_by(order).all()    
    if posts:
      ind=posts.index(post)
      if ind+1<len(posts):
        return posts[ind+1]
    return None

  def previousPost(self, post, order, required=None, textFilter=''):
    '''Returns previous post in this feed or None'''
    posts=self.getQuery()
    if required:
      posts=posts.filter(sql.or_(Post.id==post.id, required==True))
    if textFilter:
      posts=posts.filter(sql.or_(Post.id==post.id,Post.title.like('%%%s%%'%textFilter), Post.content.like('%%%s%%'%textFilter)))
    posts=posts.order_by(order).all()
    if posts:
      ind=posts.index(post)
      if ind>0:
        return posts[ind-1]
    return None

  def previousUnreadPost(self, post, order, required=None, textFilter=''):
    '''Returns previous post in this feed or None'''
    posts=self.getQuery().filter(sql.or_(Post.unread==True, Post.id==post.id))
    if required:
      posts=posts.filter(sql.or_(Post.id==post.id, required==True))
    if textFilter:
      posts=posts.filter(sql.or_(Post.id==post.id,Post.title.like('%%%s%%'%textFilter), Post.content.like('%%%s%%'%textFilter)))
    posts=posts.order_by(order).all()
    if posts:
      ind=posts.index(post)
      if ind>0:
        return posts[ind-1]
    return None

# UI Classes
from PyQt4 import QtGui, QtCore, QtWebKit
from ui.Ui_main import Ui_MainWindow
from ui.Ui_about import Ui_Dialog as UI_AboutDialog
from ui.Ui_filterwidget import Ui_Form as UI_FilterWidget
from ui.Ui_searchwidget import Ui_Form as UI_SearchWidget
from ui.Ui_feed_properties import Ui_Dialog as UI_FeedPropertiesDialog

class PostModel(QtGui.QStandardItemModel):
  def __init__(self):
    QtGui.QStandardItemModel.__init__(self)
    self.setColumnCount(2)
    self.setHeaderData(0, QtCore.Qt.Horizontal, QtCore.QVariant("Title"))
    self.setHeaderData(1, QtCore.Qt.Horizontal, QtCore.QVariant("Date"))
    self.sort(1, QtCore.Qt.DescendingOrder) # Date, descending

  def sortOrder(self):
    order=["title", "date"][self.sortingColumn]
    if self.order==QtCore.Qt.DescendingOrder:
      order=sql.desc(order)
    info("ORDER: %s", order)
    return order

  def sort(self, column, order):
    info ("Changing post model sort order to %d %d", column, order)
    self.sortingColumn=column
    self.order=order
    self.emit(QtCore.SIGNAL("resorted()"))

  def data(self, index, role):
    if not index.isValid():
      return QtCore.QVariant()
      
    if role<>QtCore.Qt.DisplayRole:
      return QtGui.QStandardItemModel.data(self, index, role)
    
    if index.column()==0:
      item=self.itemFromIndex(index)
      v=QtCore.QVariant(unicode(item.post))
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
      self.ui.updatePeriod.setEnabled(True)
      self.ui.updateUnit.setEnabled(True)
      self.ui.customUpdate.setChecked(True)
      if feed.updateInterval==0:
        i=3
      elif feed.updateInterval%1440==0:
        i=2
      elif feed.updateInterval%60==0:
        i=1
      else:
        i=0
      self.ui.updateUnit.setCurrentIndex(i)
      self.ui.updatePeriod.setValue(feed.updateInterval/([1, 60, 1440, 1][i]))
      
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
    feed.markRead=self.ui.markRead.isChecked()
    feed.loadFull=self.ui.loadFull.isChecked()
    
    if self.ui.customUpdate.isChecked():
      multiplier=[1, 60, 1440, 0][self.ui.updateUnit.currentIndex()]
      feed.updateInterval=self.ui.updatePeriod.value()*multiplier

    if self.ui.useDefault.isChecked(): # Default expire
      feed.archiveType=0
    elif self.ui.keepAll.isChecked(): # Keep everything
      feed.archiveType=1
    elif self.ui.limitCount.isChecked(): # Limit by count
      feed.archiveType=2
      feed.limitCount=self.ui.count.value()
    elif self.ui.limitDays.isChecked(): # Limit by age
      feed.archiveType=3
      feed.limitDays=self.ui.days.value()
    elif self.ui.noArchive.isChecked(): # Don't archive
      feed.archiveType=4


    elixir.session.flush()
    QtGui.QDialog.accept(self)
 
class MainWindow(QtGui.QMainWindow):
  def __init__(self):
    QtGui.QMainWindow.__init__(self)

    # Internal indexes
    self.feedItems={}
    self.postItems={}
    self.posts=[]
    self.currentFeed=None
    self.currentPost=None
    
    # View mode FIXME: make configurable
    self.combinedView=False
    
    # Set up the UI from designer
    self.ui=Ui_MainWindow()
    self.ui.setupUi(self)
    
    # add widgets to status bar
    self.progress=QtGui.QProgressBar()
    self.progress.setFixedWidth(120)
    self.ui.statusBar.addPermanentWidget(self.progress)
    
    # Use custom delegate to paint feed and post items
    self.ui.feeds.setItemDelegate(FeedDelegate(self))
    self.ui.posts.setItemDelegate(PostDelegate(self))

    # Article filter fields
    self.filterWidget=FilterWidget()
    self.ui.filterBar.addWidget(self.filterWidget)
    QtCore.QObject.connect(self.filterWidget.ui.filter, QtCore.SIGNAL("returnPressed()"), self.filterPosts)
    QtCore.QObject.connect(self.filterWidget.ui.clear, QtCore.SIGNAL("clicked()"), self.unFilterPosts)
    QtCore.QObject.connect(self.filterWidget.ui.statusCombo, QtCore.SIGNAL("currentIndexChanged(int)"), self.filterPostsByStatus)
    self.statusFilter=None
    self.textFilter=''
        
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
    QtWebKit.QWebSettings.globalSettings().setUserStyleSheetUrl(QtCore.QUrl(cssFile))
    QtCore.QObject.connect(self.ui.view.page(), QtCore.SIGNAL(" linkHovered ( const QString & link, const QString & title, const QString & textContent )"), self.linkHovered)

    # Set sorting for post list
    self.ui.posts.sortByColumn(1, QtCore.Qt.DescendingOrder)

    # Fill with feed data
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
      self.activateWindow()
      self.raise_()

  def loadPreferences(self):
    
    v=config.getValue('ui', 'showStatus', True)
    self.ui.actionStatus_Bar.setChecked(v)
    self.on_actionStatus_Bar_triggered(v)
    
    v=config.getValue('ui', 'showOnlyUnreadFeeds', False)
    self.ui.actionShow_Only_Unread_Feeds.setChecked(v)
    self.on_actionShow_Only_Unread_Feeds_triggered(v)

  def getCurrentPost(self):
    index=self.ui.posts.currentIndex()
    if index.isValid():         
      if index.column()<>0:
        index=self.ui.posts.model().index(index.row(), 0, index.parent())
      return self.ui.posts.model().itemFromIndex(index).post
    return None

  def on_actionDelete_Article_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    info ("Deleting post: %s", curPost)
    if QtGui.QMessageBox.question(None, "Delete Article - uRSSus", 
        'Are you sure you want to delete "%s"'%curPost, 
        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No ) == QtGui.QMessageBox.Yes:
      curPost.delete()
      elixir.session.flush()
      self.open_feed(self.ui.feeds.currentIndex())

  def on_actionMark_as_Read_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    if curPost.unread:
      info ("Marking as read post: %s", curPost)
      curPost.unread=False
      curPost.feed.curUnread-=1 
      elixir.session.flush()
      self.updatePostItem(curPost)
      self.updateFeedItem(curPost.feed)

  def on_actionMark_as_Unread_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    if not curPost.unread:
      info ("Marking as unread post: %s", curPost)
      curPost.unread=True
      curPost.feed.curUnread+=1
      elixir.session.flush()
      self.updatePostItem(curPost)
      self.updateFeedItem(curPost.feed)

  def on_actionOpen_in_Browser_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    QtGui.QDesktopServices.openUrl(QtCore.QUrl(curPost.link))


  def on_actionMark_as_Important_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    info ("Marking as important post: %s", curPost)
    curPost.important=True
    elixir.session.flush()
    self.updatePostItem(curPost)

  def on_actionRemove_Important_Mark_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    info ("Marking as not important post: %s", curPost)
    curPost.important=False
    elixir.session.flush()
    self.updatePostItem(curPost)


  def on_posts_customContextMenuRequested(self, pos=None):
    # FIXME: handle selections
    if pos==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    menu=QtGui.QMenu()
    menu.addAction(self.ui.actionOpen_in_Browser)
    menu.addSeparator()
    if curPost.important:
      menu.addAction(self.ui.actionRemove_Important_Mark)
    else:
      menu.addAction(self.ui.actionMark_as_Important)
    if curPost.unread:
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
      menu.addAction(self.ui.actionExpire_Feed)
      menu.addAction(self.ui.actionDelete_Feed)
      menu.exec_(QtGui.QCursor.pos())

  def on_actionExpire_Feed_triggered(self, i=None):
    if i==None: return
    index=self.ui.feeds.currentIndex()
    if index.isValid():         
      curFeed=self.ui.feeds.model().itemFromIndex(index).feed
    info ("Expiring feed: %s", curFeed)
    curFeed.expire(expunge=True)
    # Update feed display (number of unreads may have changed)
    self.updateFeedItem(curFeed)
    # Reopen it because the post list probably changed
    self.open_feed(index)

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
      elixir.session.flush()
      self.initTree()
      self.ui.feeds.setCurrentIndex(self.ui.feeds.model().indexFromItem(self.feedItems[newFeed.id]))
      self.on_actionEdit_Feed_triggered(True)

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
      elixir.session.flush()
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

  def filterPostsByStatus(self, status=None):
    if status==None: return
    
    if status==0: # All articles
      info ("No filtering by status")
      self.statusFilter=None
    elif status==1: # Unread
      info ("Filtering by status: unread")
      self.statusFilter=Post.unread
    elif status==2: # Important
      info ("Filtering by status: important")
      self.statusFilter=Post.important
    self.open_feed(self.ui.feeds.currentIndex())
      
  def unFilterPosts(self):
    self.textFilter=''
    self.filterWidget.ui.filter.setText('')
    info("Text filter removed")
    self.open_feed(self.ui.feeds.currentIndex())

  def filterPosts(self):
    self.textFilter=unicode(self.filterWidget.ui.filter.text())
    info("Text filter set to: %s", self.textFilter)
    self.open_feed(self.ui.feeds.currentIndex())

  def linkHovered(self, link, title, content):
    # FIXME: doesn't trigger. Maybe I need to reconnect after 
    # I set the contents of the webview?
    self.ui.statusBar.showMessage(link)

  def on_view_linkClicked(self, url):
    QtGui.QDesktopServices.openUrl(url)

  def on_view_loadStarted(self):
    self.progress.show()
    self.progress.setValue(0)

  def on_view_loadProgress(self, p):
    self.progress.setValue(p)

  def on_view_loadFinished(self):
    self.progress.setValue(0)
    self.progress.hide()

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
      info("updateFeedStatus: %d %d", action, id)
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
        # Force recount after update
        feed.curUnread=-1
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
    
  def on_feeds_clicked(self, index):
    item=self.model.itemFromIndex(index)
    if not item: return
    self.open_feed(index)
    if self.combinedView:
      self.open_feed(index)
    else:
      self.ui.view.setHtml(renderTemplate('feed.tmpl', feed=item.feed))

  def on_actionNormal_View_triggered(self, i=None):
    if i==None: return
    info("Switch to normal view")
    if self.combinedView:
      self.combinedView=False
      self.ui.posts.show()
      self.ui.actionNormal_View.setEnabled(False)
      self.ui.actionCombined_View.setEnabled(True)
      self.open_feed(self.ui.feeds.currentIndex())

  def on_actionCombined_View_triggered(self, i=None):
    if i==None: return
    info("Switch to combined view")    
    if not self.combinedView:
      self.combinedView=True
      self.ui.posts.hide()
      self.ui.actionNormal_View.setEnabled(True)
      self.ui.actionCombined_View.setEnabled(False)
      self.open_feed(self.ui.feeds.currentIndex())

  def resortPosts(self):
    info ("Resorting posts")
    if self.currentPost:
      cpid=self.currentPost.id
      info ("cpid=%d", cpid)
    else:
      cpid=-1
    self.open_feed(self.ui.feeds.currentIndex())
    if cpid in self.postItems:
      self.ui.posts.setCurrentIndex(self.ui.posts.model().indexFromItem(self.postItems[cpid]))
      self.currentPost=Post.get_by(id=cpid)

  def open_feed(self, index):
    item=self.model.itemFromIndex(index)
    if not item: return
    self.ui.feeds.setCurrentIndex(index)
    feed=item.feed
    self.currentFeed=feed
    # Scroll the feeds view so this feed is visible
    self.ui.feeds.scrollTo(self.ui.feeds.model().indexFromItem(self.feedItems[self.currentFeed.id]))
    self.postItems={}
    self.posts=[]
    self.currentPost=None
    
    actions=[ self.ui.actionNext_Article,
              self.ui.actionNext_Unread_Article,  
              self.ui.actionPrevious_Article,  
              self.ui.actionPrevious_Unread_Article,  
              self.ui.actionMark_as_Read,  
              self.ui.actionMark_as_Unread,  
              self.ui.actionMark_as_Important,  
              self.ui.actionDelete_Article,  
              self.ui.actionOpen_in_Browser,  
              self.ui.actionRemove_Important_Mark,  
             ]
    
    if self.combinedView: # All items filtered, as a page
      info("Opening combined")
      if feed.xmlUrl: # A regular feed
        self.posts=Post.query.filter(Post.feed==feed)
      else: # A folder
        self.posts=feed.allPostsQuery()
      # Filter by text according to the contents of self.textFilter
      if self.textFilter:
        self.posts=self.posts.filter(sql.or_(Post.title.like('%%%s%%'%self.textFilter), Post.content.like('%%%s%%'%self.textFilter)))
      if self.statusFilter:
        self.posts=self.posts.filter(self.statusFilter==True)
      # FIXME: find a way to add sorting to the UI for this (not very important)
      self.posts=self.posts.order_by(sql.desc(Post.date)).all()
      self.ui.view.setHtml(renderTemplate('combined.tmpl',posts=self.posts))
      for post in self.posts:
        self.postItems[post.id]=item
        
      for action in actions:
        action.setEnabled(False)

    else: # Standard View
      info ("Opening in standard view")
      self.ui.posts.__model=PostModel()
      self.ui.posts.setModel(self.ui.posts.__model)
      QtCore.QObject.connect(self.ui.posts.__model, QtCore.SIGNAL("resorted()"), self.resortPosts)

      # Update window title
      if feed.title:
        self.setWindowTitle("%s - uRSSus"%item.feed.title)
      elif feed.text:
        self.setWindowTitle("%s - uRSSus"%item.feed.text)
      else:
        self.setWindowTitle("uRSSus")
      
      # Sorting according to the model
      sk=self.ui.posts.model().sortOrder()
      
      if feed.xmlUrl: # A regular feed
        self.posts=Post.query.filter(Post.feed==feed)
      else: # A folder
        self.posts=feed.allPostsQuery()
      # Filter by text according to the contents of self.textFilter
      if self.textFilter:
        self.posts=self.posts.filter(sql.or_(Post.title.like('%%%s%%'%self.textFilter), Post.content.like('%%%s%%'%self.textFilter)))
      if self.statusFilter:
        self.posts=self.posts.filter(self.statusFilter==True)
      self.posts=self.posts.order_by(sk)
      self.posts=self.posts.all()
    
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

      for action in actions:
        action.setEnabled(True)

      self.ui.view.setHtml(renderTemplate('feed.tmpl',feed=feed))
      # Scroll post view to the top
      if self.posts:
        self.ui.posts.scrollTo(self.ui.posts.model().indexFromItem(self.postItems[self.posts[0].id]))


  def updatePostItem(self, post):
    if not post.id in self.postItems: #post is not being displayed
      return
      
    if self.combinedView: # The post items are not visible anyway
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

  def updateFeedItem(self, feed, parents=False, updating=False):
    info("Updating item for feed %d", feed.id)
    if not feed.id in self.feedItems:
      return
    item=self.feedItems[feed.id]
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
    item.setText(unicode(feed))
    if parents: # Not by default because it's slow
      # Update all ancestors too, because unread counts and such change
      while feed.parent:
        self.updateFeedItem(feed.parent, True)
        feed=feed.parent

  def on_posts_clicked(self, index=None, item=None):
    if item: post=item.post
    else: 
      if index.column()<>0:
        index=self.ui.posts.model().index(index.column(), 0, index.parent())
      post=self.ui.posts.model().itemFromIndex(index).post
    self.currentPost=post
    if post.unread:
      post.unread=False
      post.feed.curUnread-=1
      elixir.session.flush()
    self.updateFeedItem(post.feed, parents=True)
    self.updatePostItem(post)
    if post.feed.loadFull and post.link:
      # If I pass post.link, it crashes if I click something else quickly
      self.ui.statusBar.showMessage("Opening %s"%post.link)
      self.ui.view.setUrl(QtCore.QUrl(QtCore.QString(post.link)))
    else:
      self.ui.view.setHtml(renderTemplate('post.tmpl',post=post))

  def on_actionExport_Feeds_triggered(self, i=None):
    if i==None: return
    fname = unicode(QtGui.QFileDialog.getSaveFileName(self, "Save as", os.getcwd(), 
                                              "OPML files (*.opml *.xml)"))
    if fname:
      exportOPML(fname)

  def on_actionImport_Feeds_triggered(self, i=None):
    if i==None: return
    fname = unicode(QtGui.QFileDialog.getOpenFileName(self, "Open OPML file", os.getcwd(), 
                                              "OPML files (*.opml *.xml)"))
    if fname:
      importOPML(fname)
      self.initTree()
      
  def on_actionTechnorati_Top_100_triggered(self, i=None):
    if i==None: return
    if QtGui.QMessageBox.question(None, "Technorati Top 100 - uRSSus", 
       'You are about to import Technorati\'s Top 100 feeds for today.\nClick Yes to confirm.', 
       QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No ) == QtGui.QMessageBox.Yes:
      
      url='http://elliottback.com/tools/top100/technorati-100-to-opml.php'
      data=urlopen(url).read()
      # Create a 'Top 100' folder if there isn't one
      t100=Feed.get_by_or_init(text='Top 100')
      if not t100.parent:
        t100.parent=root_feed
      [h, name]=tempfile.mkstemp()
      tf=os.fdopen(h, 'wb+')
      tf.write(data)
      tf.flush()
      tf.close()
      importOPML(name, parent=t100)
      os.unlink(name)
      self.initTree()
      self.ui.feeds.setCurrentIndex(self.ui.feeds.model().indexFromItem(self.feedItems[t100.id]))
    
      
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
      elixir.session.flush()
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
        parent=item.feed.parent

        # Clean posts list
        self.ui.posts.setModel(PostModel())
        self.ui.view.setHtml('')

        # Trigger update on parent item
        parent.curUnread=-1
        # I really, really shouldn't have to do this. But it doesn'twork if I don't so...
        parent.children.remove(item.feed)
        self.updateFeedItem(parent, parents=True)

        # No feed current
        self.ui.feeds.setCurrentIndex(QtCore.QModelIndex())
        self.currentFeed=None

        del(self.feedItems[item.feed.id])
        item.feed.delete()
        self.ui.feeds.model().removeRow(index.row(), index.parent())
        elixir.session.flush()
        
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
  
    p = processing.Process(target=feedUpdater)
    p.setDaemon(True)
    p.start()
    processes.append(p)
    
  def on_actionNext_Unread_Article_triggered(self, i=None):
    if i==None: return
    info( "Next Unread Article")
    if not self.currentFeed:
      self.on_actionNext_Unread_Feed_triggered(True)
    if self.currentPost:
      post=self.currentPost
    elif self.posts: 
      post=self.posts[0]
    else: # No posts in this feed, just go the next unread feed
      self.on_actionNext_Unread_Feed_triggered(True)
    if post.unread: # Quirk, should redo the flow
      nextPost=post
    else:
      nextPost=self.currentFeed.nextUnreadPost(post, self.ui.posts.model().sortOrder(), self.statusFilter)
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
      nextPost=self.currentFeed.nextPost(self.currentPost, self.ui.posts.model().sortOrder(), self.statusFilter)
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
      previousPost=self.currentFeed.previousUnreadPost(post, self.ui.posts.model().sortOrder(), self.statusFilter)
    elif self.posts: # Not on a specific post, go to the last unread article
      previousPost=self.posts[-1]
      if not previousPost.unread:
        previousPost=self.currentFeed.previousUnreadPost(previousPost, self.ui.posts.model().sortOrder(), self.statusFilter)
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
      previousPost=self.currentFeed.previousPost(post, self.ui.posts.model().sortOrder(), self.statusFilter)
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
  
def exportOPML(fname):
  from OPML import Outline, OPML
  from cgi import escape
  def exportSubTree(parent, node):
    if not node.children:
      return
    for feed in node.children:
      co=Outline()
      co['text']=feed.text or ''
      if feed.xmlUrl:
        co['type']='rss'
        co['xmlUrl']=escape(feed.xmlUrl) or ''
        co['htmlUrl']=escape(feed.htmlUrl) or ''
        co['title']=escape(feed.title) or ''
        co['description']=escape(feed.description) or ''
      parent.add_child(co)
      
  opml=OPML()
  root=Outline()
  for feed in root_feed.children:
    exportSubTree(root, feed)
  opml.outlines=root._children
  opml.output(open(fname, 'w'))
    
def importOPML(fname, parent=None):
  global root_feed
  if parent == None:
    parent=root_feed

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
  for node in tree.find('//body').getchildren():
    importSubTree(parent, node)
  elixir.session.flush()

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
          try: # we can't let this fail or it will stay marked forever;-)
            feed.update()
          except:
            pass
          feedStatusQueue.put([1, feed.id])

from BeautifulSoup import BeautifulStoneSoup 
def decodeString(s):
  '''Decode HTML strings so you don't get &lt; and all those things.'''
  u=unicode(BeautifulStoneSoup(s,convertEntities=BeautifulStoneSoup.HTML_ENTITIES ))
  return u

def main():
  global root_feed
  initDB()
    
  if len(sys.argv)>1:
      # Import a OPML file into the DB so we have some data to work with
      importOPML(sys.argv[1], root_feed)
  app=QtGui.QApplication(sys.argv)
  window=MainWindow()
  
  # This will start the background fetcher as a side effect
  window.on_actionAbort_Fetches_triggered(True)
  window.show()
  sys.exit(app.exec_())
  
if __name__ == "__main__":
  main()
