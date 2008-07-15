# -*- coding: utf-8 -*-

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


class FeedTreeModel():
  "A Qt model to display categories/feeds/posts"
  

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
