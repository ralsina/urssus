import sys
from PyQt4 import QtGui, QtCore

class FeedTreeWidget(QtGui.QTreeView):
  def __init__ (self, parent):
    QtGui.QTreeView.__init__(self, parent)
    print "Created FeedTreeWidget"
    
