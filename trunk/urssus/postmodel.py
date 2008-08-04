from globals import *
from dbtables import *
from PyQt4 import QtGui, QtCore


class PostModel(QtGui.QStandardItemModel):
  def __init__(self, parent, feed=None, textFilter=None, statusFilter=None):
    QtGui.QStandardItemModel.__init__(self, parent)
    self.feed=feed
    self.textFilter=textFilter
    self.statusFilter=statusFilter
    self.setSortRole(QtCore.Qt.UserRole)
    self.initData()
    self.sort(1, QtCore.Qt.DescendingOrder) # Date, descending
 
  def initData(self):
    self.clear()
    self.postDict={}
    self.setColumnCount(2)
    self.setHeaderData(0, QtCore.Qt.Horizontal, QtCore.QVariant("Title"))
    self.setHeaderData(1, QtCore.Qt.Horizontal, QtCore.QVariant("Date"))

    self.postItems={}
    
    if self.feed.xmlUrl: # A regular feed
      self.posts=Post.query.filter(Post.feed==self.feed).filter(Post.deleted==False)
    else: # A folder
      self.posts=self.feed.allPostsQuery()
    # Filter by text according to the contents of self.textFilter
    if self.textFilter:
      self.posts=self.posts.filter(sql.or_(Post.title.like('%%%s%%'%self.textFilter), 
                                           Post.content.like('%%%s%%'%self.textFilter)))
    if self.statusFilter:
      self.posts=self.posts.filter(self.statusFilter==True)
#    self.posts=self.posts.order_by(self.sortOrder())
  
    posts=list(self.posts.all())
    for post in posts:
      item1=QtGui.QStandardItem()
      item1.setToolTip('%s - Posted at %s'%(unicode(post), unicode(post.date)))
      item1.setData(QtCore.QVariant(unicode(post)), QtCore.Qt.DisplayRole)
      item1.setData(QtCore.QVariant(unicode(post)), QtCore.Qt.UserRole)
      item1.setData(QtCore.QVariant(post.id), QtCore.Qt.UserRole+1)

      item2=QtGui.QStandardItem()
      item2.setData(QtCore.QVariant(unicode(post.date)), QtCore.Qt.DisplayRole)
      item2.setToolTip('%s - Posted at %s'%(unicode(post), unicode(post.date)))
      d=post.date
      qd=QtCore.QVariant(QtCore.QDateTime(QtCore.QDate(d.year, d.month, d.day), 
                                          QtCore.QTime(d.hour, d.minute, d.second)))
      item2.setData(qd, QtCore.Qt.UserRole)
      
      self.postItems[post.id]=[item1, item2]
      self.appendRow([item1, item2])
      self.updateItem(post)
    self.reset()
    self.emit(QtCore.SIGNAL("resorted()"))
 
  def indexFromPost(self, post):
    if post and post.id in self.postItems:
      return self.indexFromItem(self.postItems[post.id])
    return QtCore.QModelIndex()
    
  def postFromIndex(self, index):
    if index.column()<>0:
      index=self.index(index.row(), 0, index.parent())      
    item=self.itemFromIndex(index)
    if item:
      id=item.data(QtCore.Qt.UserRole).toInt()[0]
      return Post.get_by(id=id)
    return None

  def updateItem(self, post):
    if not post.id in self.postItems: #post is not being displayed
      return
    item1, item2=self.postItems[post.id]
    # FIXME: respect the palette
    if post.important:
      item1.setForeground(QtGui.QColor("red"))
      item2.setForeground(QtGui.QColor("red"))
    elif post.unread:
      item1.setForeground(QtGui.QColor("darkgreen"))
      item2.setForeground(QtGui.QColor("darkgreen"))
    else:
      item1.setForeground(QtGui.QColor("black"))
      item2.setForeground(QtGui.QColor("black"))
      
    f=item1.font()
    if post.important or post.unread:
      f.setBold(True)
    else:
      f.setBold(False)
    item1.setFont(f)
    item2.setFont(f)
