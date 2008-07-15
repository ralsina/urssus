# -*- coding: utf-8 -*-


# DB Classes
from elixir import * 

metadata.bind = "sqlite:///urssus.sqlite"
metadata.bind.echo = True

class Feed(Entity):
  htmlUrl = Field(Unicode)
  title   = Field(Unicode)
  text    = Field(Unicode)
  description = Field(Unicode)

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

if __name__ == "__main__":
  import sys
  # For starters, lets import a OPML file into the DB so we have some data to work with
  from xml.etree import ElementTree
  tree = ElementTree.parse(sys.argv[1])
  for outline in tree.findall("//outline"):
    if outline.get('xmlUrl'):
      print outline.get('title')

  
