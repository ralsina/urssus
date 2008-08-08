from globals import *
from dbtables import *
from PyQt4 import QtGui, QtCore

# constants
draggable = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled
droppable = QtCore.Qt.ItemIsDropEnabled
editable  = QtCore.Qt.ItemIsEditable

folderflags=draggable|droppable
feedflags=draggable

class FeedModel(QtGui.QStandardItemModel):
  def __init__(self, parent):
    self.flags={}
    self.feedItems={}
    self.feedCache={}
    QtGui.QStandardItemModel.__init__(self, parent)
    self.initData()

  def setData(self, index, value, role):
    if role==QtCore.Qt.EditRole:
      # Find the feed for this index
      item=self.itemFromIndex(index)
      if item:
        feed=Feed.get_by(id=item.data(QtCore.Qt.UserRole).toInt()[0])
        feed.text=unicode(value.toString())
        elixir.session.flush()
    return QtGui.QStandardItemModel.setData(self, index, value, role)
    

  def initData(self):
    self.clear()
    self.setColumnCount(2)
    self.setHeaderData(0, QtCore.Qt.Horizontal, QtCore.QVariant("Title"))
    self.setHeaderData(1, QtCore.Qt.Horizontal, QtCore.QVariant("Unread"))
    
    # Internal function
    def addSubTree(parentItem, feed):
      item1=QtGui.QStandardItem(unicode(feed))
      item1.setToolTip(unicode(feed))
      item1.setData(QtCore.QVariant(feed.id), QtCore.Qt.UserRole)
      if feed.xmlUrl:
        item1.setFlags(feedflags|editable)
      else:
        item1.setFlags(folderflags|editable)
        
      
      item2=QtGui.QStandardItem(unicode(feed.unreadCount() or ''))
      item2.setToolTip(unicode(feed.unreadCount()))
      item2.setData(QtCore.QVariant(feed.id), QtCore.Qt.UserRole)
      item2.setTextAlignment(QtCore.Qt.AlignRight)
      if feed.xmlUrl:
        item2.setFlags(feedflags &~ QtCore.Qt.ItemIsDropEnabled)
      else:
        item2.setFlags(folderflags &~ QtCore.Qt.ItemIsDropEnabled)
      
      
      parentItem.appendRow([item1, item2])

      self.feedItems[feed.id]=[item1, item2]
      if feed.xmlUrl:
        item1.setIcon(QtGui.QIcon(":/urssus.svg"))
      else:
        item1.setIcon(QtGui.QIcon(":/folder.svg"))
        for child in feed.children:
          addSubTree(item1, child)
          
    iroot=self.invisibleRootItem()
    self.feedItems[root_feed.id]=[iroot, None]
    addSubTree(iroot, root_feed)
#    for root in root_feed.children:
#      addSubTree(iroot, root)

    self.reset()

  def removeRow(self, row, parent):
    # Remove the feed from the DB
    feed=self.feedFromIndex(self.index(row, 0, parent))
    feed.delete()
    return QtGui.QStandardItemModel.removeRow(self, row, parent)

  def supportedDropActions(self):
    return QtCore.Qt.MoveAction
  
  def dropMimeData(self, data, action, row, column, parent):
    print "DROP"
    destIndex=self.index(row, column, parent)
    destItem=self.itemFromIndex(destIndex)
    if destItem:
      beforeFeed=Feed.get_by(id=destItem.data(QtCore.Qt.UserRole).toInt()[0])
    else:
      beforeFeed=None
    
    parentItem=self.itemFromIndex(parent)
    if parentItem:
      parentFeed=Feed.get_by(id=parentItem.data(QtCore.Qt.UserRole).toInt()[0])
    else:
      parentFeed=None
    # This all means, source should be now child of parentFeed, and be right 
    # before beforeFeed.
    # If beforeFeed==None, then it should be last
    print "Dropped on ", beforeFeed, parentFeed
    
    # Decoding the source data
    print list(data.formats())
    idlist=[int(id) for id in str(data.text()).split(',')]
    print "IDLIST:", idlist
    for id in idlist:
      feed=Feed.get_by(id=id)
      if beforeFeed: #insert
        idx=parentFeed.children.index(beforeFeed)
        l=parentFeed.children[:idx]+[feed]+parentFeed.children[idx:]
        i=0
        for f in l:
          f.position=i
          i+=1
      else: #append
        if parentFeed.children:
          feed.position=parentFeed.children[-1].position+1
        else:
          feed.position=0
      feed.parent=parentFeed
    elixir.session.flush()
    return QtGui.QStandardItemModel.dropMimeData(self, data, action, row, column, parent)

  def mimeTypes(self):
    return QtCore.QStringList(['application/x-qabstractitemmodeldatalist','text/plain' ])
    
  def mimeData(self, indexes):
    data=[]
    for index in list(indexes):
      item=self.itemFromIndex(index)
      id=item.data(QtCore.Qt.UserRole).toInt()[0]
      data.append(str(id))
    v=QtGui.QStandardItemModel.mimeData(self, indexes)
    print "DATAFORMATS1:", list(v.formats())
    v.setText(','.join(data) )
    return v
      
  def hasFeed(self, id):
    return id in self.feedItems
      
  def feedFromIndex(self, index):
    item=self.itemFromIndex(index)
    if item:
      id=item.data(QtCore.Qt.UserRole).toInt()[0]
      return Feed.get_by(id=id)
    return None
    
  def indexFromFeed(self, feed):
    if feed.id in self.feedItems:
      return self.indexFromItem(self.feedItems[feed.id][0])
    else:
      return QtCore.QModelIndex()
