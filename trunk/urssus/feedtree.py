# -*- coding: utf-8 -*-
from PyQt4 import QtGui,QtCore
import sys
variant=QtCore.QVariant
from pprint import pprint
import dbtables as db
import elixir
from globals import *
from norm import normalizar

# constants
draggable = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled
droppable = QtCore.Qt.ItemIsDropEnabled
editable  = QtCore.Qt.ItemIsEditable
enabled   = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable 

id_map={}

class Node(QtGui.QTreeWidgetItem):
    def __init__(self,feed):
        QtGui.QTreeWidgetItem.__init__(self,1005)
        self.setIcon(0,feed.getIcon())
        if feed.xmlUrl: # A plain feed:
          self.setFlags(draggable|editable)
        else: # A folder
          self.setFlags(draggable|editable|droppable)
        self.feed=feed
        id_map[feed.id]=self
        self.setTextAlignment(1,QtCore.Qt.AlignRight)
        # Add children too
        self.addChildren([Node(c) for c in self.feed.children])
        
    def data(self,column,role):
        if role==QtCore.Qt.DisplayRole:
            if column==0:
                return QtCore.QVariant(self.feed.text)
            elif column==1:
                return QtCore.QVariant(self.feed.unreadCount())
        elif role==QtCore.Qt.FontRole:
          f=self.treeWidget().font()
          if self.feed.unreadCount():
            f.setBold(True)
          else:
            f.setBold(False)
          return QtCore.QVariant(f)
        return QtGui.QTreeWidgetItem.data(self,column,role)

    def insertChild(self, index, child):
        QtGui.QTreeWidgetItem.insertChild(self, index, child)
        if child.feed.is_open:
          child.setExpanded(True)
          
    def __lt__(self, other):
      column=self.treeWidget().sortColumn()
      if column==1:
        return self.feed.unreadCount()<other.feed.unreadCount()
      else:
#        if not self.feed.xmlUrl and other.feed.xmlUrl:
#          return True
        return normalizar(self.feed.text.lower())<normalizar(other.feed.text.lower())

class FeedTree(QtGui.QTreeWidget):
    def __init__(self,parent=None):
        QtGui.QTreeWidget.__init__(self,parent)
        self.setColumnCount(2)
        self.setHeaderLabels(['Title','Unread'])
        self.draggedFeed=None
        
    def addTopLevelItem(self, item):
        QtGui.QTreeWidget.addTopLevelItem(self, item)
        if item.feed.is_open:
          item.setExpanded(True)
          
    def order_by(self):
      critical("order_by")
      header=self.header()
      order=header.sortIndicatorOrder()
      column=header.sortIndicatorSection()
      
      if order==QtCore.Qt.DescendingOrder: order_by='-'
      else:
        order_by=''
      if column==0:
        order_by+='text'
      else:
        order_by+='unreadCount'
      return order_by
      

    def initTree(self):
        self.clear()
        for mf in db.MetaFeed.query.all():
          item=Node(mf)
          item.setFlags(enabled)
          self.addTopLevelItem(item)
        self.root_item=Node(db.root_feed)
        self.addTopLevelItem(self.root_item)
        self.setSortingEnabled(True)
        self.sortItems(0, QtCore.Qt.AscendingOrder)
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)
        
    def mimeData(self, items):
        # Add feed-ids in the mimeData, so I know what feeds are dragged
        m=QtGui.QTreeWidget.mimeData(self, items)
        m.setText(",".join([str(i.feed.id) for i in items]))
        return m
      
    def dropEvent(self, ev):
        parentItem=self.itemAt(ev.pos())
        if not parentItem.flags() & droppable:
          # Dropping on a feed, not a folder. See if the parent is a folder and drop there
          parentItem=parentItem.parent()
          if not parentItem.flags() & droppable:
            return # Do nothing
        
        # Can drop on parentItem
        parent=parentItem.feed
        ids=[int(i) for i in ev.mimeData().text().split(',')]
        try:
          for id in ids:
            child=db.Feed.get_by(id=id)
            child.parent=parent
          elixir.session.commit()
        except:
          elixir.session.rollback()
        # Do normal drop
        return QtGui.QTreeWidget.dropEvent(self, ev)
            
    def itemFromFeed(self, feed):
        return id_map.get(feed.id, None)
            
    def setCurrentFeed(self, feed):
      item=id_map.get(feed.id, None)
      if item:
        self.setCurrentItem(item)
            
def main():
    db.initDB()
    app=QtGui.QApplication(sys.argv)
    tree=FeedTree()
    tree.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
  main()
