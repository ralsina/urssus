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
    if self.xmlUrl:
      return self.text+'(%d)'%Post.query.filter(Post.feed==self).filter(Post.unread==True).count()
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
         
        # FIXME: doesn'twork right with DanShanoff.com 
        # Author if available, else None
        author=''
        # First, we may have author_detail, which is the nicer one
        if 'author_detail' in post:
          ad=post['author_detail']
          # How much detail?
          if 'name' in ad:
            author=ad['name']
            if 'href' in ad:
              author='<a href="%s">%s</a>'%(ad['href'], author)
          if 'author_email' in ad:
            author+=' - <a href="mailto:%s">%s</a>'%(ad['email'], ad['email'])
        # Or maybe just an author
        elif 'author' in post:
          author=post['author']
          
        # But we may have a list of contributors
        if 'contributors' in post:
          # Which may have the same detail as the author's
          for contrib in post['contributors']:
            cont=''
            if 'name' in contrib:
              cont=contrib['name']
              if 'href' in contrib:
                cont='<a href="%s">%s</a>'%(contrib['href'], cont)
            if 'email' in contrib:
              cont+=' - <a href="mailto:%s">%s</a>'%(contrib['email'], contrib['email'])
            author+=' - '+cont
        if not author:
          author=None
          
        # The link should be simple ;-)
        link=post['link']
          
        posts.append(Post.get_by_or_init(feed=self, date=date, title=post['title'], 
                                         post_id=post[idkey], content=content, 
                                         author=author, link=link))
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
    self.initTree()

  def initTree(self):
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
    iroot=QtGui.QStandardItem("All Feeds")
    iroot.feed=None
    self.model.appendRow(iroot)
    for root in roots:
      nn=addSubTree(iroot, root)
      
    self.ui.feeds.expandAll()
    
  def on_feeds_clicked(self, index):
    item=self.model.itemFromIndex(index)
    feed=item.feed
    
    if not feed or not feed.xmlUrl:
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
    post.unread=False
    session.flush()
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

  def on_actionFetch_Feed_triggered(self, i=None):
    if i==None: return
    # Start an immediate update for the current feed
    item=self.model.itemFromIndex(self.ui.feeds.currentIndex())
    if item and item.feed:
      # FIXME: move to out-of-process
      item.feed.update()

  def on_actionFetch_All_Feeds_triggered(self, i=None):
    if i==None: return
    global processes
    # Start an immediate update for all feeds
    print "fetching all feeds"
    p = processing.Process(target=feedUpdater, args=(True, ))
    p.setDaemon(True)
    p.start()
    processes.append(p)
    
  def on_actionAbort_Fetches_triggered(self, i=None):
    if i==None: return
    global processes
    print "Aborting all fetches ", processes
    # stop all processes and restart the background timed fetcher
    for proc in processes:
      proc.terminate()
      print "Terminated: ", proc.isAlive(), proc.getExitCode()
    processes=[]
    
    p = processing.Process(target=feedUpdater)
    p.setDaemon(True)
    p.start()
    processes.append(p)
    print "processes ", processes
    
  def on_actionNext_Unread_Article_triggered(self, i=None):
    if i==None: return
    print "Next Unread"
    
  def on_actionNext_Article_triggered(self, i=None):
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
        #FIXME: need to go to the next feed and open the first post
    else:
      # Is there any item in this model?
      if self.ui.posts.model() and self.ui.posts.__model.rowCount()>0:
        self.ui.posts.setCurrentIndex(self.ui.posts.__model.indexFromItem(self.ui.posts.__model.item(0)))
      else: # No items here, we need to go somewhere else
        print "No posts"
        #FIXME: needs to go to the next feed and open the frst post
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
def feedUpdater(full=False):
  initDB()
  if full:
      for feed in Feed.query.filter(Feed.xmlUrl<>None):
        feed.update()
  else:
    while True:
      print "updater loop"
      now=datetime.now()
      for feed in Feed.query.filter(Feed.xmlUrl<>None):
        if (now-feed.lastUpdated).seconds>1800:
          print "updating because of timeout"
          feed.update()
      print "---------------------"
      time.sleep(60)

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

