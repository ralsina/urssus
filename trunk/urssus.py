# -*- coding: utf-8 -*-

import sys, os, time, processing
from datetime import datetime, timedelta

# Mark Pilgrim's feed parser
import feedparser as fp

# DB Classes
from elixir import * 

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
    return self.text
    
  def update(self):
    print "Updating: ", self.title
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
        posts.append(Post.get_by_or_init(feed=self, date=date, title=post['title'], post_id=post[idkey], content=content))
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

def initDB():
  # This is just temporary
  metadata.bind = "sqlite:///urssus.sqlite"
  # metadata.bind.echo = True
  setup_all()
  if not os.path.exists("urssus.sqlite"):
    create_all()

# UI Classes
from PyQt4 import QtGui, QtCore
from Ui_main import Ui_MainWindow

class MainWindow(QtGui.QMainWindow):
  def __init__(self):
    QtGui.QMainWindow.__init__(self)
  
    # Set up the UI from designer
    self.ui=Ui_MainWindow()
    self.ui.setupUi(self)
  
    # Initialize the tree from the Feeds
    self.model=QtGui.QStandardItemModel()
    self.ui.feeds.setModel(self.model)
    
    # Internal function
    def addSubTree(parent, node):
      nn=QtGui.QStandardItem(unicode(node))
      parent.appendRow(nn)
      nn.feed=node
      for child in node.children:
        addSubTree(nn, child)
      return nn
          
    roots=Feed.query.filter(Feed.parent==None)
    iroot=self.model.invisibleRootItem()
    iroot.feed=None
    for root in roots:
      nn=addSubTree(iroot, root)
      
    self.ui.feeds.expandAll()
    
  def on_feeds_clicked(self, index):
    item=self.model.itemFromIndex(index)
    feed=item.feed
    
    if not feed.xmlUrl:
      return
    posts=Post.query.filter(Post.feed==feed).order_by("-date")
    self.ui.posts.__model=QtGui.QStandardItemModel()
    for post in posts:
      item=QtGui.QStandardItem(post.title)
      item.post=post
      self.ui.posts.__model.appendRow(item)
    self.ui.posts.setModel(self.ui.posts.__model)
      
  def on_posts_clicked(self, index):
    item=self.ui.posts.__model.itemFromIndex(index)
    post=item.post
    self.ui.view.setHtml(post.content)

  def on_actionFetch_Feed_activated(self):
    # Start an immediate update for the current feed
    item=self.model.itemFromIndex(self.ui.feeds.currentIndex())
    if item and item.feed:
      # FIXME move to out-of-process
      item.feed.update()

  def on_actionFetch_All_Feeds_activated(self):
    # Start an immediate update for all feeds
    print "fetching all feeds"
    # FIXME move to out-of-process
    for feed in Feed.query.all():
      feed.update()
      
def importOPML(fname):
  from xml.etree import ElementTree
  tree = ElementTree.parse(fname)
  current=None
  for outline in tree.findall("//outline"):
    xu=outline.get('xmlUrl')
    if xu:
      f=Feed.get_by(xmlUrl=outline.get('xmlUrl'), 
             htmlUrl=outline.get('htmlUrl'), 
             )
      if not f:
        f=Feed(xmlUrl=outline.get('xmlUrl'), 
             htmlUrl=outline.get('htmlUrl'), 
             title=outline.get('title'),
             text=outline.get('text'), 
             description=outline.get('description')
             )        
        if current:
          current.children.append(f)
          f.parent=current
    else:
      current=Feed.get_by_or_init(text=outline.get('text'))
    session.flush()

# The feed updater (runs out-of-process)
def feedUpdater():
  initDB()
  while True:
    print "updater loop"
    now=datetime.now()
    for feed in Feed.query.filter(Feed.xmlUrl<>None):
      if (now-feed.lastUpdated).seconds>1800:
        feed.update()
    print "---------------------"
    time.sleep(3)

if __name__ == "__main__":
  p = processing.Process(target=feedUpdater)
  p.setDaemon(True)
  p.start()
  
  initDB()
  
  if not p.isAlive(): #Sometimes we get a little contention here, no big deal I hope
    p.start()
  
  if len(sys.argv)>1:
      # Import a OPML file into the DB so we have some data to work with
      importOPML(sys.argv[1])
  app=QtGui.QApplication(sys.argv)
  window=MainWindow()
  window.show()
  sys.exit(app.exec_())

