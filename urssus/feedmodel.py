from globals import *
from dbtables import *
from PyQt4 import QtGui, QtCore

class FeedModel(QtGui.QStandardItemModel):
  def __init__(self):
    QtGui.QStandardItemModel.__init__(self)
#    self.setHeaderData(0, QtCore.Qt.Horizontal, QtCore.QVariant("Title"))
#    self.setHeaderData(1, QtCore.Qt.Horizontal, QtCore.QVariant("Unread"))
#    self.setHeaderData(2, QtCore.Qt.Horizontal, QtCore.QVariant("Id"))
#    
#  def columnCount(self, parent):
#    return 3

  def supportedDropActions(self):
    return QtCore.Qt.MoveAction
    
  def flags(self, index):
    r = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
    if index.isValid():
      item=self.itemFromIndex(index)
      id=item.data(QtCore.Qt.UserRole).toInt()[0]
      feed=Feed.get_by(id=id)
      if feed and not feed.xmlUrl: # a folder
        r=r | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled
      else:
        r=r | QtCore.Qt.ItemIsDragEnabled
      return r
      
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
        feed.position=parentFeed.children[-1].position+1
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
      
  def feedFromIndex(self, index):
    item=self.itemFromIndex(index)
    if item:
      return Feed.get_by(id=item.data(QtCore.Qt.UserRole).toInt()[0])
    return None
