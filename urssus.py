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
    if self.xmlUrl:
      return self.text+'(%d)'%Post.query.filter(Post.feed==self).filter(Post.unread==True).count()
    return self.text
    
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
        p = Post.get_by(feed=self, date=date, title=post['title'],post_id=post[idkey])
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
from Ui_about import Ui_Dialog as UI_AboutDialog

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
    
    # Fill with feed data
    self.initTree()
    
    # Timer to trigger status bar updates
    self.statusTimer=QtCore.QTimer()
    self.statusTimer.setSingleShot(True)
    QtCore.QObject.connect(self.statusTimer, QtCore.SIGNAL("timeout()"), self.updateStatusBar)
    self.statusTimer.start(0)
    
  def on_actionStatus_Bar_triggered(self, i=None):
    if i==None: return
    if self.ui.actionStatus_Bar.isChecked():
      self.statusBar().show()
    else:
      self.statusBar().hide()
      
    
  def on_actionAbout_uRSSus_triggered(self, i=None):
    if i==None: return
    AboutDialog().exec_()
    
  def updateStatusBar(self):
    if not statusQueue.empty():
      msg=statusQueue.get()
      self.statusBar().showMessage(msg)
    else:
      self.statusBar().showMessage("")      
    if statusQueue.empty():
      self.statusTimer.start(1000)
    else:
      self.statusTimer.start(150)


  def initTree(self):
    # Initialize the tree from the Feeds
    self.model=QtGui.QStandardItemModel()
    self.ui.feeds.setModel(self.model)
    
    # Internal function
    def addSubTree(parent, node):
      nn=QtGui.QStandardItem(unicode(node))
      parent.appendRow(nn)
      nn.feed=node
      if node.children:
        nn.setIcon(QtGui.QIcon(":/folder.svg"))
        for child in node.children:
          addSubTree(nn, child)
      else:
        nn.setIcon(QtGui.QIcon(":/urssus.svg"))
      return nn
          
    roots=Feed.query.filter(Feed.parent==None)
    iroot=QtGui.QStandardItem("All Feeds")
    iroot.feed=None
    self.model.appendRow(iroot)
    for root in roots:
      nn=addSubTree(iroot, root)
      
    self.ui.feeds.expandAll()
    
  def on_view_loadProgress(self, p):
    self.statusBar().showMessage("Page loaded %d%%"%p)
    
  def on_feeds_clicked(self, index):
    item=self.model.itemFromIndex(index)
    feed=item.feed
    
    if not feed or not feed.xmlUrl:
      # FIXME: implement "aggregated feeds" when the user clicks on a folder
      return
    self.setWindowTitle("%s - uRSSus"%feed.title)
      
    posts=Post.query.filter(Post.feed==feed).order_by(sql.desc("date"))
    self.ui.posts.__model=QtGui.QStandardItemModel()
    for post in posts:
      item=QtGui.QStandardItem('%s - %s'%(post.title, post.date))
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
      self.on_feeds_clicked(self.ui.feeds.currentIndex())

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
    global processes, statusQueue
    statusQueue.put("Aborting all fetches")
    # stop all processes and restart the background timed fetcher
    for proc in processes:
      proc.terminate()
    processes=[]
    # Since we terminate forcefully, the contents of the
    # queue are probably corrupted. So throw them away.
    statusQueue=processing.Queue()
    
    p = processing.Process(target=feedUpdater)
    p.setDaemon(True)
    p.start()
    processes.append(p)
    
  def on_actionNext_Unread_Article_triggered(self, i=None):
    if i==None: return
    print "Next Unread"
    # FIXME: This should not be **soooooo** recursive ;-)
    self.on_actionNext_Article_triggered(True, True)
    
  def on_actionNext_Article_triggered(self, i=None, unread=False):
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
        self.on_actionNext_Article_triggered(True)
    else:
      # Are there any item in this model?
      if self.ui.posts.model() and self.ui.posts.model().rowCount()>0:
        # Then go to the first one
        self.ui.posts.setCurrentIndex(self.ui.posts.model().index(0, 0))
      else: # No items here, we need to go to the next feed
        print "No posts"
        self.on_actionNext_Feed_triggered(True)
        self.on_actionNext_Article_triggered(True)
    if unread:
      it=self.ui.posts.model().itemFromIndex(self.ui.posts.currentIndex())
      if not it.post.unread:
        self.on_actionNext_Article_triggered(True, True)
        
    self.on_posts_clicked(self.ui.posts.currentIndex())

  def on_actionNext_Feed_triggered(self, i=None):
    if i==None: return
    print "Next Feed"
    nextIndex=None
    # First see if we are on a specific feed
    curIndex=self.ui.feeds.currentIndex()
    if curIndex.isValid():
      # If there is a child, go there
      if self.model.hasChildren(curIndex):
        nextIndex=curIndex.child(0, 0)
      else:
        # No childs, see if there is a next sibling
        nextIndex=curIndex.sibling(curIndex.row()+1, 0)
        while not nextIndex.isValid(): #If invalid, go parent and next
          nextIndex=curIndex.parent().sibling(curIndex.parent().row()+1, 0)
        
    else: # Just go to the first feed there is
      i=self.ui.feeds.model().index(0, 0) # This one always exists, it's the "all feeds"
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
        self.on_actionNext_Feed_triggered(True)
      else: # Finally!
        self.on_feeds_clicked(nextIndex)

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

