# -*- coding: utf-8 -*-

# Mark Pilgrim's feed parser
import feedparser as fp

# DB Classes
from elixir import * 

metadata.bind = "sqlite:///urssus.sqlite"
metadata.bind.echo = True

class Feed(Entity):
  htmlUrl     = Field(Text)
  xmlUrl      = Field(Text)
  title       = Field(Text)
  text        = Field(Text)
  description = Field(Text)
  children    = OneToMany('Feed')
  parent      = ManyToOne('Feed')
  posts       = OneToMany('Post')
  def __repr__(self):
    return self.text
    
  def update(self):
    d=fp.parse(self.xmlUrl)
    
class Post(Entity):
  feed        = ManyToOne('Feed')
  title       = Field(Text)
  post_id     = Field(Text)
  content     = Field(Text)

# This is just temporary
setup_all()
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
    
    # Internal function
    def addSubTree(parent, node):
      nn=QtGui.QStandardItem(unicode(node))
      parent.appendRow(nn)
      nn.feed=node
      if not node.children:
        return
      else:
        for child in node.children:
          addSubTree(nn, child)
          
    roots=Feed.query.filter(Feed.parent==None)
    iroot=self.model.invisibleRootItem()
    iroot.feed=None
    for root in roots:
      addSubTree(iroot, root)
      
    self.ui.feeds.setModel(self.model)
    
    QtCore.QObject.connect(self.ui.feeds, QtCore.SIGNAL("clicked(QModelIndex)"), self.openFeed)

  def openFeed(self, index):
    item=self.model.itemFromIndex(index)
    feed=item.feed
    
    if not feed.xmlUrl:
      return
      
    d=fp.parse(feed.xmlUrl)
    posts=[]
    for post in d['entries']:
      print post
      print '----------------------------------\n\n'
      if 'content' in post:
        posts.append(Post(feed=feed, title=post['title'], post_id=post['id'], content='<hr>'.join([ c.value for c in post['content']])))
      elif 'summary' in post:
        posts.append(Post(feed=feed, title=post['title'], post_id=post['id'], content=post['summary']))
      elif 'value' in post:
        posts.append(Post(feed=feed, title=post['title'], post_id=post['id'], content=post['value']))
    session.flush()

    self.ui.posts.__model=QtGui.QStandardItemModel()
    for post in posts:
      item=QtGui.QStandardItem(post.title)
      item.post=post
      self.ui.posts.__model.appendRow(item)
    self.ui.posts.setModel(self.ui.posts.__model)
      

if __name__ == "__main__":
  import sys
  # For starters, lets import a OPML file into the DB so we have some data to work with
  from xml.etree import ElementTree
  tree = ElementTree.parse(sys.argv[1])
  current=None
  for outline in tree.findall("//outline"):
    xu=outline.get('xmlUrl')
    if xu:
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
      current=Feed(text=outline.get('text'))
    session.flush()
  app=QtGui.QApplication(sys.argv)
  window=MainWindow()
  window.show()
  sys.exit(app.exec_())

