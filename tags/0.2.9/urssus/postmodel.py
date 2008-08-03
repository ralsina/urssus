from globals import *
from dbtables import *
from PyQt4 import QtGui, QtCore


class PostModel(QtGui.QStandardItemModel):
  def __init__(self, parent, feed=None, textFilter=None, statusFilter=None):
    QtGui.QStandardItemModel.__init__(self, parent)
    self.feed=feed
    self.textFilter=textFilter
    self.statusFilter=statusFilter
    self.sort(1, QtCore.Qt.DescendingOrder) # Date, descending
 
  def initData(self):
    self.clear()
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
    self.posts=self.posts.order_by(self.sortOrder())
  
    for post in self.posts.all():
      item=QtGui.QStandardItem()
      item.setToolTip('Posted at %s'%unicode(post.date))
      self.appendRow(item)
      self.postItems[post.id]=item
      self.updateItem(post)
      item.setData(QtCore.QVariant(post.id), QtCore.Qt.UserRole)
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

    item=self.postItems[post.id]
    index=self.indexFromItem(item)
    index2=self.index(index.row(), 1, index.parent())
    item2=self.itemFromIndex(index2)
    # FIXME: respect the palette
    if post.important:
      item.setForeground(QtGui.QColor("red"))
#      item2.setForeground(QtGui.QColor("red"))
    elif post.unread:
      item.setForeground(QtGui.QColor("darkgreen"))
#      item2.setForeground(QtGui.QColor("darkgreen"))
    else:
      item.setForeground(QtGui.QColor("black"))
#      item2.setForeground(QtGui.QColor("black"))
      
    f=item.font()
    if post.important or post.unread:
      f.setBold(True)
    else:
      f.setBold(False)
    item.setFont(f)
#    item2.setFont(f)

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
    self.initData()

  def data(self, index, role):
    if not index.isValid():
      return QtCore.QVariant()
      
    # Parent class handles icon/font/etc.
    if role<>QtCore.Qt.DisplayRole:
      return QtGui.QStandardItemModel.data(self, index, role)
    
    if index.column()==0:
      v=QtCore.QVariant(decodeString(unicode(self.postFromIndex(index))))
    elif index.column()==1:
      # Tricky!
      ind=self.index(index.row(), 0, index.parent())
      post=self.postFromIndex(ind)
      if not post:
        #No data
        return QtCore.QVariant()

      # Be smarter, let's see how it looks
      now=datetime.now()
      if post.date.date()==now.date(): # Today, showthe time
        v=QtCore.QVariant(str(post.date.time()))
      else:
        v=QtCore.QVariant(str(post.date.date()))
    else:
      return QtCore.QVariant()
    return v
