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

from __future__ import with_statement
from globals import *
from dbtables import *
from PyQt4 import QtGui, QtCore

# constants
draggable = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled
droppable = QtCore.Qt.ItemIsDropEnabled
editable  = QtCore.Qt.ItemIsEditable
# Roles used in the items
feed_id=QtCore.Qt.UserRole
display=QtCore.Qt.DisplayRole
position=QtCore.Qt.UserRole+1

folderflags=draggable|droppable
feedflags=draggable

class FeedModel(QtGui.QStandardItemModel):
  def __init__(self, parent):
    self.flags={}
    self.feedIndex={}
    self.feedCache={}
    QtGui.QStandardItemModel.__init__(self, parent)
    self.bfont=QtGui.QApplication.font()
    self.bfont.setBold(True)
    self.initData()
    
  def setData(self, index, value, role):
    if role==QtCore.Qt.EditRole:
      # Find the feed for this index
      item=self.itemFromIndex(index)
      if item:
        try:
          feed=Feed.get_by(id=item.data(feed_id).toInt()[0])
          feed.text=unicode(value.toString())
          elixir.session.commit()
        except:
          elixir.session.rollback()
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
      item1.setData(QtCore.QVariant(feed.id), feed_id)
      item1.setData(QtCore.QVariant(feed.position), position)
      if feed.xmlUrl:
        item1.setFlags(feedflags|editable)
      else:
        item1.setFlags(folderflags|editable)
        
      count=feed.unreadCount()
      item2=QtGui.QStandardItem(unicode(count or ''))
      item2.setToolTip(unicode(count))
      item2.setData(QtCore.QVariant(feed.id), feed_id)
      item2.setData(QtCore.QVariant(feed.position), position)
      item2.setTextAlignment(QtCore.Qt.AlignRight)
      if feed.xmlUrl:
        item2.setFlags(feedflags &~ QtCore.Qt.ItemIsDropEnabled)
      else:
        item2.setFlags(folderflags &~ QtCore.Qt.ItemIsDropEnabled)
      
      if count:
        item1.setFont(self.bfont)
        item2.setFont(self.bfont)
      
      parentItem.appendRow([item1, item2])

      self.feedIndex[feed.id]=[self.indexFromItem(item1), self.indexFromItem(item2)]
      item1.setIcon(feed.getIcon())
      if not feed.xmlUrl:
        for child in feed.getChildren():
          addSubTree(item1, child)
          
    iroot=self.invisibleRootItem()
    # First all metafeeds with no parents
    for mf in MetaFeed.query.filter(MetaFeed.parent==None):
      addSubTree(iroot, mf)
    # Now the feeds
    self.feedIndex[root_feed.id]=[self.indexFromItem(iroot), QtCore.QModelIndex()]
    addSubTree(iroot, root_feed)

  def removeRow(self, row, parent):
    # Remove the feed from the DB
    feed=self.feedFromIndex(self.index(row, 0, parent))
    if feed: feed.delete()
    return QtGui.QStandardItemModel.removeRow(self, row, parent)

  def supportedDropActions(self):
    return QtCore.Qt.MoveAction
  
  def dropMimeData(self, data, action, row, column, parent):
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
    info("Dropped before: %s , parent: %s", beforeFeed, parentFeed)
    
    # Decoding the source data
    idlist=[int(id) for id in str(data.text()).split(',')]
    info ("IDLIST: %s", str(idlist))
    try:
      for id in idlist:
        # Do feed housekeeping
        feed=Feed.get_by(id=id)
        if beforeFeed: #insert
          children=parentFeed.getChildren()
          idx=children.index(beforeFeed)
          l=children[:idx]+[feed]+children[idx:]
          i=0
          for f in l:
            f.position=i
            i+=1
        else: #append
          children=parentFeed.getChildren()
          if children:
            feed.position=children[-1].position+1
          else:
            feed.position=0
        feed.parent=parentFeed
      elixir.session.commit()
    except:
      elixir.session.rollback()

    self.emit(QtCore.SIGNAL("dropped(PyQt_PyObject)"), feed)
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
    v.setText(','.join(data) )
    return v
      
  def hasFeed(self, id):
    return id in self.feedIndex
      
  def feedFromIndex(self, index):
    item=self.itemFromIndex(index)
    if item:
      id=item.data(feed_id).toInt()[0]
      return Feed.get_by(id=id)
    return None
    
  def indexFromFeed(self, feed):
    if feed.id in self.feedIndex:
      return self.feedIndex[feed.id][0]      
    else:
      return QtCore.QModelIndex()

  def sort(self, column, _order):
    order = [1,-1][_order]
    print "ORDER", order
    if column==0:
      for f in Feed.query.all():
        f.children.sort(cmp=lambda x, y:order*cmp(x.text, y.text))
    elif column==1:
      for f in Feed.query.all():
        f.children.sort(cmp=lambda x, y:order*cmp(x.unreadCount(), y.unreadCount()))

    QtGui.QStandardItemModel.sort(self, column, _order)
