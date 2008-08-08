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

import sys, os, time, urlparse, tempfile, codecs, traceback
from urllib import urlopen
from datetime import datetime, timedelta
from dbtables import Post, Feed, initDB
import elixir
import sqlalchemy as sql


# Twitter support
try:
  from twitter import Twitter
except ImportError:
  Twitter=None
from tiny import tiny


from globals import *
from feedupdater import feedUpdater

# UI Classes
from PyQt4 import QtGui, QtCore, QtWebKit
from ui.Ui_main import Ui_MainWindow
from ui.Ui_about import Ui_Dialog as UI_AboutDialog
from ui.Ui_filterwidget import Ui_Form as UI_FilterWidget
from ui.Ui_searchwidget import Ui_Form as UI_SearchWidget
from ui.Ui_feed_properties import Ui_Dialog as UI_FeedPropertiesDialog
from ui.Ui_twitterpost import Ui_Dialog as UI_TwitterDialog
from ui.Ui_twitterauth import Ui_Dialog as UI_TwitterAuthDialog
from ui.Ui_greaderimport import Ui_Dialog as UI_GReaderDialog
from ui.Ui_bugdialog import Ui_Dialog as UI_BugDialog
from ui.Ui_configdialog import Ui_Dialog as UI_ConfigDialog

from processdialog import ProcessDialog

from postmodel import *
from feedmodel import * 

class FilterWidget(QtGui.QWidget):
  def __init__(self):
    QtGui.QWidget.__init__(self)
    # Set up the UI from designer
    self.ui=UI_FilterWidget()
    self.ui.setupUi(self)
    
class SearchWidget(QtGui.QWidget):
  def __init__(self):
    QtGui.QWidget.__init__(self)
    # Set up the UI from designer
    self.ui=UI_SearchWidget()
    self.ui.setupUi(self)

class GReaderDialog(QtGui.QDialog):
  def __init__(self, parent):
    QtGui.QDialog.__init__(self, parent)
    # Set up the UI from designer
    self.ui=UI_GReaderDialog()
    self.ui.setupUi(self)

class BugDialog(QtGui.QDialog):
  def __init__(self):
    QtGui.QDialog.__init__(self)
    # Set up the UI from designer
    self.ui=UI_BugDialog()
    self.ui.setupUi(self)

class ConfigDialog(QtGui.QDialog):
  def __init__(self, parent):
    QtGui.QDialog.__init__(self, parent)
    # Set up the UI from designer
    self.ui=UI_ConfigDialog()
    self.ui.setupUi(self)
    pages=[]
    sections=[]
    self.values={}

    for sectionName, options in config.options:
      # Create a page widget/layout for this section:
      page=QtGui.QScrollArea()
      layout=QtGui.QGridLayout()
      row=-2
      for optionName, definition in options:
        row+=2
        if definition[0]=='bool':
          cb=QtGui.QCheckBox(optionName)
          cb.setChecked(config.getValue(sectionName, optionName, definition[1]))
          layout.addWidget(cb, row, 0, 1, 2)
          self.values[sectionName+'/'+optionName]=[cb, lambda(cb): cb.isChecked()]

          
        elif definition[0]=='int':
          label=QtGui.QLabel(optionName+":")
          label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
          spin=QtGui.QSpinBox()
          if definition[3] is not None:
            spin.setMinimum(definition[3])
          else:
            spin.setMinimum(-99999)
          if definition[4] is not None:
            spin.setMaximum(definition[4])
          else:
            spin.setMaximum(99999)
          spin.setValue(config.getValue(sectionName, optionName, definition[1]))
          layout.addWidget(label, row, 0, 1, 1)
          layout.addWidget(spin, row, 1, 1, 1)
          self.values[sectionName+'/'+optionName]=[spin, lambda(spin): spin.value()]
          
        elif definition[0]=='string':
          label=QtGui.QLabel(optionName+":")
          label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
          text=QtGui.QLineEdit()
          text.setText(config.getValue(sectionName, optionName, definition[1]))          
          layout.addWidget(label, row, 0, 1, 1)
          layout.addWidget(text, row, 1, 1, 1)
          self.values[sectionName+'/'+optionName]=[text, lambda(text): unicode(text.text())]

        elif definition[0]=='password':
          label=QtGui.QLabel(optionName+":")
          label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
          text=QtGui.QLineEdit()
          text.setEchoMode(QtGui.QLineEdit.Password)
          text.setText(config.getValue(sectionName, optionName, definition[1]))          
          layout.addWidget(label, row, 0, 1, 1)
          layout.addWidget(text, row, 1, 1, 1)
          self.values[sectionName+'/'+optionName]=[text, lambda(text): unicode(text.text())]

        help=QtGui.QLabel(definition[2])
        help.setWordWrap(True)
        layout.addWidget(help, row, 2, 1, 1)
        separator=QtGui.QFrame()
        separator.setFrameStyle(QtGui.QFrame.HLine|QtGui.QFrame.Plain)
        layout.addWidget(separator, row+1, 0, 1, 3)
      page.setLayout(layout)      
      pages.append(page)
      sections.append(sectionName)

    for page, name in zip(pages,sections) :
      # Make a tab out of it
      self.ui.tabs.addTab(page, name)
    self.ui.tabs.setCurrentIndex(1)
    self.ui.tabs.removeTab(0)

    

  def accept(self):
    for k in self.values:
      sec, opt=k.split('/')
      widget, l = self.values[k]
      config.setValue(sec, opt, l(widget))
    QtGui.QDialog.accept(self)

def my_excepthook(exc_type, exc_value, exc_traceback):
  if exc_type<>KeyboardInterrupt:
    msg = ' '.join(traceback.format_exception(exc_type,
                                              exc_value,
                                              exc_traceback,20))
    dlg=BugDialog()
    dlg.ui.report.setText('''Version: %s\n\n%s'''%(VERSION, msg))
    dlg.exec_()
  # Call the default exception handler if you want
  sys.__excepthook__(exc_type, exc_value, exc_traceback)


  
class AboutDialog(QtGui.QDialog):
  def __init__(self, parent):
    QtGui.QDialog.__init__(self, parent)
    # Set up the UI from designer
    self.ui=UI_AboutDialog()
    self.ui.setupUi(self)

class TwitterDialog(QtGui.QDialog):
  def __init__(self, parent, post):
    QtGui.QDialog.__init__(self, parent)
    # Set up the UI from designer
    self.ui=UI_TwitterDialog()
    self.ui.setupUi(self)
    self.ui.message.setPlainText('%s - %s'%(post, tiny(post.link)))
    self.u=config.getValue('twitter', 'username', None)
    self.p=config.getValue('twitter', 'password', None)
    if not self.u or not self.p:
      self.ui.ok.setEnabled(False)
      self.ui.username.setText('Authentication not configured')      
    else:
      self.ui.username.setText('Posting update as: %s'%self.u)

  def on_changeAuth_clicked(self, i=None):
    if i==None: return
    dlg=TwitterAuthDialog(self)
    dlg.ui.username.setText(unicode(self.u))
    if dlg.exec_():
      self.u=unicode(dlg.ui.username.text())
      self.p=unicode(dlg.ui.password.text())
      if dlg.ui.saveit.isChecked():
        config.setValue('twitter', 'username', self.u)
        config.setValue('twitter', 'password', self.p)
      self.ui.ok.setEnabled(True)

  def on_message_textChanged(self):
    self.ui.counter.setText(str(140-len(unicode(self.ui.message.toPlainText()))))

  def accept(self):
    status=unicode(self.ui.message.toPlainText())
    conn=Twitter(self.u, self.p)
    conn.statuses.update(source='urssus', status=status)    
    QtGui.QDialog.accept(self)
    
class TwitterAuthDialog(QtGui.QDialog):
  def __init__(self, parent):
    QtGui.QDialog.__init__(self, parent)
    # Set up the UI from designer
    self.ui=UI_TwitterAuthDialog()
    self.ui.setupUi(self)


class TrayIcon(QtGui.QSystemTrayIcon):
  def __init__(self):
    QtGui.QSystemTrayIcon.__init__ (self,QtGui.QIcon(":/urssus.svg"))
  def updateIcon(self):
    uc=root_feed.unreadCount()
    self.setToolTip('%d unread posts'%uc)
    if uc:
      self.setIcon(QtGui.QIcon(':/urssus-unread.svg'))
    else:
      self.setIcon(QtGui.QIcon(':/urssus.svg'))


class FeedProperties(QtGui.QDialog):
  def __init__(self, feed):
    QtGui.QDialog.__init__(self)
    # Set up the UI from designer
    self.ui=UI_FeedPropertiesDialog()
    self.ui.setupUi(self)
    self.ui.tabWidget.setCurrentIndex(0)
    self.feed=feed
    self.loadData()
  
  def loadData(self):
    feed=self.feed
    self.ui.name.setText(feed.text)
    self.ui.url.setText(feed.xmlUrl)
    self.ui.notify.setChecked(feed.notify)
    if feed.updateInterval==-1: # Use default
      self.ui.updatePeriod.setEnabled(False)
      self.ui.updateUnit.setEnabled(False)
      self.ui.customUpdate.setChecked(False)
    else:
      self.ui.updatePeriod.setEnabled(True)
      self.ui.updateUnit.setEnabled(True)
      self.ui.customUpdate.setChecked(True)
      if feed.updateInterval==0:
        i=3
      elif feed.updateInterval%1440==0:
        i=2
      elif feed.updateInterval%60==0:
        i=1
      else:
        i=0
      self.ui.updateUnit.setCurrentIndex(i)
      self.ui.updatePeriod.setValue(feed.updateInterval/([1, 60, 1440, 1][i]))
      
    if feed.archiveType==0: # Use default archiving
      self.ui.useDefault.setChecked(True)
    elif feed.archiveType==1: # Keep all articles
      self.ui.keepAll.setChecked(True)
    elif feed.archiveType==2: # Keep a number of articles
      self.ui.limitCount.setChecked(True)
      self.ui.count.setValue(feed.limitCount)
    elif feed.archiveType==3: # Keep for a period of time
      self.ui.limitDays.setChecked(True)
      self.ui.days.setValue(feed.limitDays)
    elif feed.archiveType==4: # Keep nothing
      self.ui.noArchive.setChecked(True)
  
    self.ui.loadFull.setChecked(feed.loadFull)
    self.ui.markRead.setChecked(feed.markRead)
    
  def accept(self):
    feed=self.feed
    feed.text=unicode(self.ui.name.text())
    # FIXME: validate
    feed.xmlUrl=unicode(self.ui.url.text())
    feed.notify=self.ui.notify.isChecked()
    feed.markRead=self.ui.markRead.isChecked()
    feed.loadFull=self.ui.loadFull.isChecked()
    
    if self.ui.customUpdate.isChecked():
      multiplier=[1, 60, 1440, 0][self.ui.updateUnit.currentIndex()]
      feed.updateInterval=self.ui.updatePeriod.value()*multiplier

    if self.ui.useDefault.isChecked(): # Default expire
      feed.archiveType=0
    elif self.ui.keepAll.isChecked(): # Keep everything
      feed.archiveType=1
    elif self.ui.limitCount.isChecked(): # Limit by count
      feed.archiveType=2
      feed.limitCount=self.ui.count.value()
    elif self.ui.limitDays.isChecked(): # Limit by age
      feed.archiveType=3
      feed.limitDays=self.ui.days.value()
    elif self.ui.noArchive.isChecked(): # Don't archive
      feed.archiveType=4


    elixir.session.flush()
    QtGui.QDialog.accept(self)

class MainWindow(QtGui.QMainWindow):
  def __init__(self):
    QtGui.QMainWindow.__init__(self)

    # Internal indexes
    self.combinedView=False
    self.showingFolder=False
    
    # Set up the UI from designer
    self.ui=Ui_MainWindow()
    self.ui.setupUi(self)
    
    # add widgets to status bar
    self.progress=QtGui.QProgressBar()
    self.progress.setFixedWidth(120)
    self.ui.statusBar.addPermanentWidget(self.progress)
    
    # Article filter fields
    self.filterWidget=FilterWidget()
    self.ui.filterBar.addWidget(self.filterWidget)
    QtCore.QObject.connect(self.filterWidget.ui.filter, QtCore.SIGNAL("returnPressed()"), self.filterPosts)
    QtCore.QObject.connect(self.filterWidget.ui.clear, QtCore.SIGNAL("clicked()"), self.unFilterPosts)
    QtCore.QObject.connect(self.filterWidget.ui.statusCombo, QtCore.SIGNAL("currentIndexChanged(int)"), self.filterPostsByStatus)
    self.statusFilter=None
    self.textFilter=''
        
    # Search widget
    self.ui.searchBar.hide()
    self.searchWidget=SearchWidget()
    self.ui.searchBar.addWidget(self.searchWidget)
    QtCore.QObject.connect(self.searchWidget.ui.next, QtCore.SIGNAL("clicked()"), self.findText)
    QtCore.QObject.connect(self.searchWidget.ui.previous, QtCore.SIGNAL("clicked()"), self.findTextReverse)
    QtCore.QObject.connect(self.searchWidget.ui.close, QtCore.SIGNAL("clicked()"), self.ui.searchBar.hide)
    QtCore.QObject.connect(self.searchWidget.ui.close, QtCore.SIGNAL("clicked()"), self.ui.view.setFocus)
    # Completion with history
    # FIXME: make persistent? Not sure
    self.searchHistory=[]
    self.filterHistory=[]

    # Set some properties of the Web view
    page=self.ui.view.page()
    page.setLinkDelegationPolicy(page.DelegateAllLinks)
    self.ui.view.setFocus(QtCore.Qt.TabFocusReason)
    QtWebKit.QWebSettings.globalSettings().setUserStyleSheetUrl(QtCore.QUrl(cssFile))
    copy_action=self.ui.view.page().action(QtWebKit.QWebPage.Copy)
    copy_action.setIcon(QtGui.QIcon(':/editcopy.svg'))
    self.ui.menu_Edit.insertAction(self.ui.actionFind, copy_action )
    self.ui.menu_Edit.insertSeparator(self.ui.actionFind)

    # Set sorting for post list
    self.ui.posts.sortByColumn(1, QtCore.Qt.DescendingOrder)

    # Fill with feed data
    self.showOnlyUnread=False
    QtCore.QTimer.singleShot(0, self.initTree)

    # Timer to trigger status bar updates
    self.statusTimer=QtCore.QTimer()
    self.statusTimer.setSingleShot(True)
    QtCore.QObject.connect(self.statusTimer, QtCore.SIGNAL("timeout()"), self.updateStatusBar)
    self.statusTimer.start(0)
    
    # Load user preferences
    self.loadPreferences()

    # Tray icon
    self.tray=TrayIcon()
    self.tray.show()
    self.notifiedFeed=None
    QtCore.QObject.connect(self.tray, QtCore.SIGNAL("messageClicked()"), self.notificationClicked)
    QtCore.QObject.connect(self.tray, QtCore.SIGNAL("activated( QSystemTrayIcon::ActivationReason)"), self.trayActivated)
    self.tray.updateIcon()
    traymenu=QtGui.QMenu(self)
    traymenu.addAction(self.ui.actionFetch_All_Feeds)
    traymenu.addSeparator()
    traymenu.addAction(self.ui.actionQuit)
    self.tray.setContextMenu(traymenu)
    
    # Add all menu actions to this window, so they still work when
    # the menu bar is hidden (tricky!)
    for action in self.ui.menuBar.actions():
      self.addAction(action)

    # Timer to mark feeds as busy/updated/whatever
    self.feedStatusTimer=QtCore.QTimer()
    self.feedStatusTimer.setSingleShot(True)
    QtCore.QObject.connect(self.feedStatusTimer, QtCore.SIGNAL("timeout()"), self.updateFeedStatus)
    self.feedStatusTimer.start(1000)
    self.updatesCounter=0

  def fixPostListUI(self):
    # Fixes for post list UI
    header=self.ui.posts.header()
    header.setStretchLastSection(False)
    header.setResizeMode(0, QtGui.QHeaderView.Stretch)
    header.setResizeMode(1, QtGui.QHeaderView.Fixed)
    header.resizeSection(1, header.fontMetrics().width(' 88/88/8888 8888:88:88 ')+4)

  def fixFeedListUI(self):
    # Fixes for feed list UI
    header=self.ui.feeds.header()
    header.setStretchLastSection(False)
    header.setResizeMode(0, QtGui.QHeaderView.Stretch)
    header.setResizeMode(1, QtGui.QHeaderView.Fixed)
    header.resizeSection(1, header.fontMetrics().width(' Unread ')+4)

  def trayActivated(self, reason=None):
    if reason == None: return
    if reason == self.tray.Trigger:
      if config.getValue('ui', 'hideOnTrayClick', True) == True and self.isVisible():
        self.hide()
      else:
        self.show()
        self.raise_()
    
  def notificationClicked(self):
    if self.notifiedFeed:
      self.open_feed(self.ui.feeds.model().indexFromFeed(self.notifiedFeed))
      self.activateWindow()
      self.raise_()

  def loadPreferences(self):
    
    v=config.getValue('ui', 'showStatus', True)
    self.ui.actionStatus_Bar.setChecked(v)
    self.on_actionStatus_Bar_triggered(v)

    v=config.getValue('ui', 'showMainBar', True)
    self.ui.toolBar.setVisible(v)
    self.ui.actionMain_Toolbar.setChecked(v)
    v=config.getValue('ui', 'showFilterBar', True)
    self.ui.filterBar.setVisible(v)
    self.ui.actionFilter_Toolbar.setChecked(v)

    v=config.getValue('ui','shortFeedList', False)
    self.ui.actionShort_Feed_List.setChecked(v)
    # This will trigger the right view mode as well
    self.on_actionShort_Feed_List_triggered(True)

    v=config.getValue('ui', 'showOnlyUnreadFeeds', False)
    self.ui.actionShow_Only_Unread_Feeds.setChecked(v)
    self.on_actionShow_Only_Unread_Feeds_triggered(v)
    
    pos=config.getValue('ui', 'position', None)
    if pos:
      self.move(*pos)
    size=config.getValue('ui', 'size', None)
    if size:
      self.resize(*size)

    splitters=config.getValue('ui', 'splitters', None)
    if splitters:
      self.ui.splitter.setSizes(splitters[0])
      self.ui.splitter_2.setSizes(splitters[1])
      
  def getCurrentPost(self):
    index=self.ui.posts.currentIndex()
    if not index.isValid() or not self.ui.posts.model():
      return None
    return self.ui.posts.model().postFromIndex(index)

  def on_actionReport_Bug_triggered(self, i=None):
    if i==None: return
    QtGui.QDesktopServices.openUrl(QtCore.QUrl('http://code.google.com/p/urssus/issues/entry?template=Defect%20report%20from%20user'))

  def on_actionPreferences_triggered(self, i=None):
    if i==None: return
    dlg=ConfigDialog(self)
    dlg.exec_()

  def on_actionImport_From_Google_Reader_triggered(self, i=None):
    if i==None: return
    
    dlg=GReaderDialog(self)
    if dlg.exec_():
      # FIXME: progress reports, non-block...
      import GoogleReader.reader as gr
      reader=gr.GoogleReader()
      reader.identify(unicode(dlg.ui.username.text()), 
                      unicode(dlg.ui.password.text()))
      reader.login()
      subs=reader.get_subscription_list()['subscriptions']
      for sub in subs:
        title=sub['title']
        id=sub['id'] # Something like feed/http://lambda-the-ultimate.org/rss.xml 
        if id.startswith('feed/'):
          xmlUrl=id[5:]
        else:
          # Don't know how to handle it
          print sub
          continue
        # Treat the first category's label as a folder name.
        cats=sub['categories']
        if cats:
          fname=cats[0]['label']
        # So, with a xmlUrl and a fname, we can just create the feed
        # See if we have the folder
        folder=Feed.get_by_or_init(parent=root_feed, text=fname, xmlUrl=None)
        elixir.session.flush()
        if Feed.get_by(xmlUrl=xmlUrl):
          # Already subscribed
          # FIXME: implement progress reports
          print "You are already subscribed to %s"%xmlUrl
          continue
        f=Feed.get_by(xmlUrl=xmlUrl)
        if not f:
          newFeed=Feed(text=title, title=title, xmlUrl=xmlUrl, parent=folder)
      elixir.session.flush()
      self.initTree()
        

  def on_actionFull_Screen_triggered(self, i=None):
    if i==None: return
    if self.ui.actionFull_Screen.isChecked():
      self.showFullScreen()
    else:
      self.showNormal()
    
  def on_actionShow_Menu_Bar_triggered(self, i=None):
    if i==None: return
    if self.ui.actionShow_Menu_Bar.isChecked():
      self.ui.menuBar.show()
    else:
      self.ui.menuBar.hide()
    
  def on_actionPost_to_Twitter_triggered(self, i=None):
    if i==None: return
    info("Posting to twitter")
    post=self.getCurrentPost()
    if not post: return
    if not Twitter:
      # FIXME: complain, install, whatever
      return
      
    dlg=TwitterDialog(self, post)
    dlg.exec_()

  def on_actionDelete_Article_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    info ("Deleting post: %s", curPost)
    if QtGui.QMessageBox.question(None, "Delete Article - uRSSus", 
        'Are you sure you want to delete "%s"'%curPost, 
        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No ) == QtGui.QMessageBox.Yes:
      curPost.delete()
      elixir.session.flush()
      self.open_feed(self.ui.feeds.currentIndex())

  def on_actionMark_as_Read_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    if curPost.unread:
      info ("Marking as read post: %s", curPost)
      curPost.unread=False
      curPost.feed.curUnread-=1 
      elixir.session.flush()
      self.updatePostItem(curPost)
      self.updateFeedItem(curPost.feed, parents=True)

  def updatePostItem(self, post):
    self.ui.posts.model().updateItem(post)

  def on_actionMark_as_Unread_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    if not curPost.unread:
      info ("Marking as unread post: %s", curPost)
      curPost.unread=True
      curPost.feed.curUnread+=1
      elixir.session.flush()
      self.updatePostItem(curPost)
      self.updateFeedItem(curPost.feed, parents=True)

  def on_actionOpen_in_Browser_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    QtGui.QDesktopServices.openUrl(QtCore.QUrl(curPost.link))


  def on_actionMark_as_Important_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    info ("Marking as important post: %s", curPost)
    curPost.important=True
    elixir.session.flush()
    self.updatePostItem(curPost)

  def on_actionRemove_Important_Mark_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    info ("Marking as not important post: %s", curPost)
    curPost.important=False
    elixir.session.flush()
    self.updatePostItem(curPost)


  def on_posts_customContextMenuRequested(self, pos=None):
    # FIXME: handle selections
    if pos==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    menu=QtGui.QMenu()
    menu.addAction(self.ui.actionOpen_in_Browser)
    menu.addSeparator()
    if curPost.important:
      menu.addAction(self.ui.actionRemove_Important_Mark)
    else:
      menu.addAction(self.ui.actionMark_as_Important)
    if curPost.unread:
      menu.addAction(self.ui.actionMark_as_Read)
    else:
      menu.addAction(self.ui.actionMark_as_Unread)
    menu.addAction(self.ui.actionPost_to_Twitter)
    menu.addSeparator()
    menu.addAction(self.ui.actionDelete_Article)
    menu.exec_(QtGui.QCursor.pos())

  def on_feeds_customContextMenuRequested(self, pos=None):
    if pos==None: return
    
    feed=self.ui.feeds.model().feedFromIndex(self.ui.feeds.currentIndex())
    if feed:
      menu=QtGui.QMenu()
      menu.addAction(self.ui.actionMark_Feed_as_Read)
      menu.addSeparator()
      menu.addAction(self.ui.actionFetch_Feed)
      menu.addSeparator()
      menu.addAction(self.ui.actionOpen_Homepage)
      menu.addSeparator()
      menu.addAction(self.ui.actionEdit_Feed)
      menu.addAction(self.ui.actionExpire_Feed)
      menu.addAction(self.ui.actionDelete_Feed)
      menu.exec_(QtGui.QCursor.pos())

  def on_actionExpire_Feed_triggered(self, i=None):
    if i==None: return
    index=self.ui.feeds.currentIndex()
    if index.isValid():         
      curFeed=self.ui.feeds.model().feedFromIndex(index)
    info ("Expiring feed: %s", curFeed)
    curFeed.expire(expunge=True)
    # Update feed display (number of unreads may have changed)
    # This would trigger a merge with the post list, but since
    # the user actively expired it, we force a new postmodel
    # and reopen the feed
    self.ui.posts.setModel(None)
    self.open_feed(index)
    self.updateFeedItem(curFeed,parents=True)

  def on_actionEdit_Feed_triggered(self, i=None):
    if i==None: return
    index=self.ui.feeds.currentIndex()
    curFeed=self.ui.feeds.model().feedFromIndex(index)
    if not curFeed.xmlUrl:
      self.ui.feeds.edit(index)
      return
    info ("Editing feed: %s", curFeed)

    editDlg=FeedProperties(curFeed)
    if editDlg.exec_():
      # update feed item, no parents
      self.updateFeedItem(curFeed)
    self.open_feed(index)

  def addFeed(self, url):
    # Use Mark pilgrim / Aaron Swartz's RSS finder module
    
    # This takes a few seconds, because we need to fetch the feed and parse it
    # So, start a background process, show a dialog, and make the user wait
    dlg=ProcessDialog(self, callable=self.realAddFeed, args=[url, ])
    if dlg.exec_():
      # Retrieve the feed
      newFeed=Feed.get_by(id=dlg.result)
      # Figure out the insertion point
      index=self.ui.feeds.currentIndex()
      if index.isValid():         
        curFeed=self.ui.feeds.model().feedFromIndex(index)
      else:
        curFeed=root_feed
      # if curFeed is a feed, add as sibling
      if curFeed.xmlUrl:
        newFeed.parent=curFeed.parent
      # if curFeed is a folder, add as child
      else:
        newFeed.parent=curFeed
      elixir.session.flush()
      self.initTree()
      idx=self.ui.feeds.model().indexFromFeed(newFeed)
      self.ui.feeds.setCurrentIndex(idx)
      self.open_feed(idx)
      self.on_actionEdit_Feed_triggered(True)
    
  def realAddFeed(self, url, output):
    _info   = lambda(msg): output.put([0, msg])
    _error  = lambda(msg): output.put([2, msg])
    _return = lambda(msg): output.put([100, msg])
      
    import feedfinder
    try:
      _info('Searching for a feed in %s'%url)
      feed=feedfinder.feed(url)
    except feedfinder.TimeoutError, e:
      _error('Timeout downloading %s'%url )      
      return
    if not feed:
      _error("Can't find a feed wit URL: %s"%url)
      return
    _info ("Found feed: %s"%feed)
    _info ("Checking if you are subscribed")
    f=Feed.get_by(xmlUrl=feed)
    if f:
      # Already subscribed
      ff=unicode(f) or f.xmlUrl 
      _error('You are already subscribed to "%s"'%f)
      return
    _info ('Creating feed in the database')
    newFeed=Feed(xmlUrl=feed)
    _info ('Fetching feed information')
    newFeed.update()
    # To show it on the tree
    newFeed.text=newFeed.title
    elixir.session.flush()
    _info ('done')
    _return (newFeed.id)
    

  def on_actionAdd_Feed_triggered(self, i=None):
    if i==None: return
    # Ask for feed URL
    [url, ok]=QtGui.QInputDialog.getText(self, "Add Feed - uRSSus", "&Feed URL:")
    if ok:
      url=unicode(url)
      self.addFeed(unicode(url))

  def on_actionNew_Folder_triggered(self, i=None):
    if i==None: return
    # Ask for folder name
    [name, ok]=QtGui.QInputDialog.getText(self, "Add Folder - uRSSus", "&Folder name:")
    if ok:
      newFolder=Feed(text=unicode(name))
      # Figure out the insertion point
      index=self.ui.feeds.currentIndex()
      if index.isValid():         
        curFeed=self.ui.feeds.model().feedFromIndex(index)
      else:
        curFeed=root_feed
      # if curFeed is a feed, add as sibling
      if curFeed.xmlUrl:
        newFolder.parent=curFeed.parent
      # if curFeed is a folder, add as child
      else:
        newFolder.parent=curFeed
      elixir.session.flush()
      self.initTree()
      self.ui.feeds.setCurrentIndex(self.ui.feeds.model().indexFromFeed(newFolder))

  def on_actionShow_Only_Unread_Feeds_triggered(self, checked=None):
    if checked==None: return
    info ("Show only unread: %d", checked)
    self.showOnlyUnread=checked
    for feed in Feed.query().all():
      self.updateFeedItem(feed)
    config.setValue('ui', 'showOnlyUnreadFeeds', checked)
  
  def on_actionFind_triggered(self, i=None):
    if i==None: return
    self.ui.searchBar.show()
    self.searchWidget.ui.text.setFocus(QtCore.Qt.TabFocusReason)

  def on_actionFind_Again_triggered(self, i=None):
    if i==None: return
    self.findText()

  def updateSearchHistory(self, text):
    if not text in self.searchHistory:
      self.searchHistory.append(text)
      self.searchHistory=self.searchHistory[-20:]
      self.searchCompleter=QtGui.QCompleter(self.searchHistory, self.searchWidget.ui.text)
      self.searchCompleter.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
      self.searchWidget.ui.text.setCompleter(self.searchCompleter)
      
  def findText(self):
    text=unicode(self.searchWidget.ui.text.text())
    self.updateSearchHistory(text)      
    if self.searchWidget.ui.matchCase.isChecked():
      self.ui.view.findText(text, QtWebKit.QWebPage.FindCaseSensitively)
    else:  
      self.ui.view.findText(text)

  def findTextReverse(self):
    text=unicode(self.searchWidget.ui.text.text())
    self.updateSearchHistory(text)
    if self.searchWidget.ui.matchCase.isChecked():
      self.ui.view.findText(text, QtWebKit.QWebPage.FindBackward | QtWebKit.QWebPage.FindCaseSensitively)
    else:  
      self.ui.view.findText(text, QtWebKit.QWebPage.FindBackward)

  def filterPostsByStatus(self, status=None):
    if status==None: return
    
    if status==0: # All articles
      info ("No filtering by status")
      self.statusFilter=None
    elif status==1: # Unread
      info ("Filtering by status: unread")
      self.statusFilter=Post.unread
    elif status==2: # Important
      info ("Filtering by status: important")
      self.statusFilter=Post.important
    self.open_feed(self.ui.feeds.currentIndex())
      
  def unFilterPosts(self):
    self.textFilter=''
    self.filterWidget.ui.filter.setText('')
    self.filterWidget.ui.statusCombo.setCurrentIndex(0)
    info("Text filter removed")
    self.open_feed(self.ui.feeds.currentIndex())
    self.ui.view.setFocus(QtCore.Qt.TabFocusReason)

  def updateFilterHistory(self, text):
    if not text in self.filterHistory:
      self.filterHistory.append(text)
      self.filterHistory=self.filterHistory[-20:]
      self.filterCompleter=QtGui.QCompleter(self.filterHistory, 
                                            self)
      self.filterCompleter.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
      self.filterWidget.ui.filter.setCompleter(self.filterCompleter)

  def filterPosts(self):
    self.textFilter=unicode(self.filterWidget.ui.filter.text())
    self.updateFilterHistory(self.textFilter)
    info("Text filter set to: %s", self.textFilter)
    self.open_feed(self.ui.feeds.currentIndex())
    self.ui.view.setFocus(QtCore.Qt.TabFocusReason)

  def linkHovered(self, link, title, content):
    # FIXME: doesn't trigger. Maybe I need to reconnect after 
    # I set the contents of the webview?
    self.ui.statusBar.showMessage(link)

  def on_view_linkClicked(self, url):
    # FIXME protect against injection...
    if str(url.scheme())=='urssus':
      [_, command, post_id]=str(url.path()).split('/')
      post=Post.get_by(id=post_id)
      if command=='read':
        post.unread=False
      elif command=='unread':
        post.unread=True
      elif command=='important':
        post.important=True
      elif command=='unimportant':
        post.important=False
      elixir.session.flush()
      post.feed.curUnread=-1
      self.updateFeedItem(post.feed, parents=True)
    else:
      QtGui.QDesktopServices.openUrl(url)

  def on_view_loadStarted(self):
    self.progress.show()
    self.progress.setValue(0)

  def on_view_loadProgress(self, p):
    self.progress.setValue(p)

  def on_view_loadFinished(self):
    self.progress.setValue(0)
    self.progress.hide()

  def on_actionStatus_Bar_triggered(self, i=None):
    if i==None: return
    if self.ui.actionStatus_Bar.isChecked():
      self.statusBar().show()
    else:
      self.statusBar().hide()
    config.setValue('ui', 'showStatus', self.ui.actionStatus_Bar.isChecked())

  def on_actionMain_Toolbar_triggered(self, i=None):
    if i==None: return
    config.setValue('ui', 'showMainBar', self.ui.actionMain_Toolbar.isChecked())
    
  def on_actionFilter_Toolbar_triggered(self, i=None):
    if i==None: return
    config.setValue('ui', 'showFilterBar', self.ui.actionFilter_Toolbar.isChecked())

  def on_actionAbout_uRSSus_triggered(self, i=None):
    if i==None: return
    AboutDialog(self).exec_()
    
  def updateFeedStatus(self):
    while not feedStatusQueue.empty():
      data=feedStatusQueue.get()
      
      [action, id] = data[:2]
      info("updateFeedStatus: %d %d", action, id)
      if not self.ui.feeds.model().hasFeed(id):
        if action==4: # Add new feed
          self.addFeed(id)
          return
        elif action==5: #OPML to import
          importOPML(id, root_feed)
          self.initTree()
          return
        elif action==6: #Just pop
          self.show()
          self.raise_()
        else:
          error( "id %s not in the tree", id)
          return
      feed=Feed.get_by(id=id)
      if action==0: # Mark as updating
        self.updateFeedItem(feed, updating=True)
        self.updatesCounter+=1
      elif action==1: # Mark as finished updating
        # Force recount after update
        feed.curUnread=-1
        self.updateFeedItem(feed, updating=False)
        self.updatesCounter-=1
      elif action==2: # Update it, may have new posts, so all parents
        self.updateFeedItem(feed, parents=True, can_reopen=True)
      elif action==3: # Systray notification
        self.notifiedFeed=feed
        self.tray.showMessage("New Articles", "%d new articles in %s"%(data[2], feed.text) )
        
      if self.updatesCounter>0:
        self.ui.actionAbort_Fetches.setEnabled(True)
      else:
        self.ui.actionAbort_Fetches.setEnabled(False)

    self.feedStatusTimer.start(1000)

  def updateStatusBar(self):
    if not statusQueue.empty():
      msg=statusQueue.get()
      self.statusBar().showMessage(msg)
    else:
      self.statusBar().showMessage("")      
    if statusQueue.empty():
      self.statusTimer.start(1000)
    else:
      self.statusTimer.start(100)

  def initTree(self):
    self.setEnabled(False)
    # Initialize the tree from the Feeds
    if not self.ui.feeds.model():
      self.ui.feeds.setModel(FeedModel(self))
    else:
      self.ui.feeds.model().initData()
    self.fixFeedListUI()

    # Open all required folders
    for feed in Feed.query().filter_by(is_open=True):
      self.ui.feeds.expand(self.ui.feeds.model().indexFromFeed(feed))

    # Update all the feeds that have unread posts
    for feed in Feed.query():
      if feed.unreadCount()>0:
        self.updateFeedItem(feed)
    
    self.setEnabled(True)
    self.filterWidget.setEnabled(True)
    self.searchWidget.setEnabled(True)
    
  def on_feeds_expanded(self, index):
    feed=self.ui.feeds.model().feedFromIndex(index)
    if not feed: return
    feed.is_open=True
    elixir.session.flush()
    
  def on_feeds_collapsed(self, index):
    feed=self.ui.feeds.model().feedFromIndex(index)
    if not feed: return
    feed.is_open=False
    elixir.session.flush()
    
  def on_feeds_clicked(self, index):
    self.open_feed(index)
    feed=self.ui.feeds.model().feedFromIndex(index)
    if not feed: return
    if self.combinedView:
      self.open_feed(index)
    else:
      self.ui.view.setHtml(renderTemplate('feed.tmpl', feed=feed))

  def autoAdjustSplitters(self):
    # Surprising splitter size prevention
    h=self.height()
    w=self.width()
    self.ui.splitter.setSizes([h*.3,h*.7] )
    self.ui.splitter_2.setSizes([w*.3,w*.7] )

  def on_actionNormal_View_triggered(self, i=None):
    if i==None: return
    info("Switch to normal view")
    if self.combinedView:
      self.combinedView=False      
    if self.ui.actionShort_Feed_List.isChecked():
      self.ui.centralWidget.layout().addWidget(self.ui.splitter) 
      self.ui.centralWidget.layout().addWidget(self.ui.splitter_2) 
      self.ui.splitter_2.insertWidget(0, self.ui.feeds)
      self.ui.splitter_2.insertWidget(1, self.ui.posts)
      self.ui.splitter.insertWidget(0, self.ui.splitter_2)
      self.ui.splitter.insertWidget(1, self.ui.view_container)
      self.ui.splitter.show()
      self.ui.splitter_2.show()
    else:
      self.ui.centralWidget.layout().addWidget(self.ui.splitter) 
      self.ui.centralWidget.layout().addWidget(self.ui.splitter_2) 
      self.ui.splitter.insertWidget(0, self.ui.posts)
      self.ui.splitter.insertWidget(1, self.ui.view_container)
      self.ui.splitter_2.insertWidget(0, self.ui.feeds)
      self.ui.splitter_2.insertWidget(1, self.ui.splitter)
      self.ui.splitter.show()
      self.ui.splitter_2.show()
      
    self.ui.posts.show()
    self.ui.actionNormal_View.setEnabled(False)
    self.ui.actionCombined_View.setEnabled(True)
    self.ui.actionFancy_View.setEnabled(True)
    self.ui.actionWidescreen_View.setEnabled(True)
    self.open_feed(self.ui.feeds.currentIndex())
    config.setValue('ui', 'viewMode', 'normal')

    self.autoAdjustSplitters()

  def on_actionWidescreen_View_triggered(self, i=None):
    if i==None: return
    info("Switch to widescreen view")
    if self.combinedView:
      self.combinedView=False
    if self.ui.actionShort_Feed_List.isChecked():
      self.ui.centralWidget.layout().addWidget(self.ui.splitter) 
      self.ui.centralWidget.layout().addWidget(self.ui.splitter_2) 
      self.ui.splitter.insertWidget(0, self.ui.feeds)
      self.ui.splitter.insertWidget(1, self.ui.posts)
      self.ui.splitter_2.insertWidget(0, self.ui.splitter)
      self.ui.splitter_2.insertWidget(1, self.ui.view_container)
      self.ui.splitter.show()
      self.ui.splitter_2.show()
    else:
      self.ui.centralWidget.layout().addWidget(self.ui.splitter) 
      self.ui.centralWidget.layout().addWidget(self.ui.splitter_2) 
      self.ui.splitter_2.insertWidget(0, self.ui.feeds)
      self.ui.splitter_2.insertWidget(1, self.ui.posts)
      self.ui.splitter_2.insertWidget(2, self.ui.view_container)
      self.ui.splitter.hide()
      self.ui.splitter_2.show()

    self.ui.posts.show()
    self.ui.actionNormal_View.setEnabled(True)
    self.ui.actionCombined_View.setEnabled(True)
    self.ui.actionFancy_View.setEnabled(True)
    self.ui.actionWidescreen_View.setEnabled(False)
    self.open_feed(self.ui.feeds.currentIndex())
    config.setValue('ui', 'viewMode', 'wide')

    self.autoAdjustSplitters()

  def on_actionCombined_View_triggered(self, i=None, template='combined.tmpl'):
    if i==None: return
    info("Switch to combined view")    
    self.combinedView=True
    self.combinedTemplate=template
    if self.ui.actionShort_Feed_List.isChecked():
      self.ui.centralWidget.layout().addWidget(self.ui.splitter) 
      self.ui.centralWidget.layout().addWidget(self.ui.splitter_2)
      self.ui.splitter.insertWidget(0, self.ui.feeds)
      self.ui.splitter.insertWidget(1, self.ui.view_container)
      self.ui.splitter.show()
      self.ui.splitter_2.hide()
    else:
      self.ui.centralWidget.layout().addWidget(self.ui.splitter) 
      self.ui.centralWidget.layout().addWidget(self.ui.splitter_2)
      self.ui.splitter_2.insertWidget(0, self.ui.feeds)
      self.ui.splitter_2.insertWidget(1, self.ui.view_container)
      self.ui.splitter.hide()
      self.ui.splitter_2.show()
        
    self.ui.posts.hide()
    self.ui.actionNormal_View.setEnabled(True)
    self.ui.actionCombined_View.setEnabled(False)
    self.ui.actionFancy_View.setEnabled(True)
    self.ui.actionWidescreen_View.setEnabled(True)
    self.open_feed(self.ui.feeds.currentIndex())
    config.setValue('ui', 'viewMode', 'combined')

  def on_actionFancy_View_triggered(self, i=None):
    self.on_actionCombined_View_triggered(True, 'fancy.tmpl')
    config.setValue('ui', 'viewMode', 'fancy')
    self.ui.actionCombined_View.setEnabled(True)
    self.ui.actionFancy_View.setEnabled(False)

  def on_actionShort_Feed_List_triggered(self, i=None):
    if i==None: return
    v=config.getValue('ui', 'viewMode', 'normal')
    if v=='wide':
      self.on_actionWidescreen_View_triggered(v)
    elif v=='combined':
      self.on_actionCombined_View_triggered(v)
    elif v=='fancy':
      self.on_actionFancy_View_triggered(v)
    else:
      self.on_actionNormal_View_triggered(v)
    config.setValue('ui', 'shortFeedList', self.ui.actionShort_Feed_List.isChecked())

  def updateListedFeedItem(self):
    '''This connects to the post list model's reset signal, so we can update
    the feed item when the model data changes'''
    
    feed=Feed.get_by(id=self.ui.posts.model().feed_id)
    self.updateFeedItem(feed, parents=True)

  def open_feed(self, index):
    if not index.isValid():
      return
    feed=self.ui.feeds.model().feedFromIndex(index)
    if not feed: return
    
    if feed.xmlUrl:
      self.showingFolder=False
    else:
      self.showingFolder=True
    
    self.ui.feeds.setCurrentIndex(index)
    # Scroll the feeds view so this feed is visible
    self.ui.feeds.scrollTo(index)

    # Update window title
    if feed.title:
      self.setWindowTitle("%s - uRSSus"%feed.title)
    elif feed.text:
      self.setWindowTitle("%s - uRSSus"%feed.text)
    else:
      self.setWindowTitle("uRSSus")

    actions=[ self.ui.actionNext_Article,
              self.ui.actionNext_Unread_Article,  
              self.ui.actionPrevious_Article,  
              self.ui.actionPrevious_Unread_Article,  
              self.ui.actionMark_as_Read,  
              self.ui.actionMark_as_Unread,  
              self.ui.actionMark_as_Important,  
              self.ui.actionDelete_Article,  
              self.ui.actionOpen_in_Browser,  
              self.ui.actionRemove_Important_Mark,  
             ]
    
    if self.combinedView: # CombinedView / FancyView
      # Lose the model in self.ui.posts
      self.ui.posts.setModel(None)
    
      info("Opening combined")
      if feed.xmlUrl: # A regular feed
        self.posts=Post.query.filter(Post.feed==feed)
        showFeedInPosts=True
      else: # A folder
        self.posts=feed.allPostsQuery()
        showFeedInPosts=False
      # Filter by text according to the contents of self.textFilter
      if self.textFilter:
        self.posts=self.posts.filter(sql.or_(Post.title.like('%%%s%%'%self.textFilter), Post.content.like('%%%s%%'%self.textFilter)))
      if self.statusFilter:
        self.posts=self.posts.filter(self.statusFilter==True)
      # FIXME: find a way to add sorting to the UI for this (not very important)
      self.posts=self.posts.order_by(sql.desc(Post.date)).all()
      self.ui.view.setHtml(renderTemplate(self.combinedTemplate, posts=self.posts, showFeed=showFeedInPosts))

      for action in actions:
        action.setEnabled(False)

    else: # StandardView / Widescreen View
      info ("Opening in standard view")
      
      # Remember current post
      if self.ui.posts.model():
        post=self.ui.posts.model().postFromIndex(self.ui.posts.currentIndex())
      else:
        post=None

      model=self.ui.posts.model()
      # The == are weird because sqlalchemy reimplementes the == operator for
      # model.statusFilter
      if model and model.feed_id==feed.id and \
            str(model.textFilter)==str(self.textFilter) and \
            str(model.statusFilter)==str(self.statusFilter):
        self.ui.posts.model().initData(update=True)
      else:
        self.ui.posts.setModel(PostModel(self.ui.posts, feed, self.textFilter, self.statusFilter))
        QtCore.QObject.connect(self.ui.posts.model(), QtCore.SIGNAL("modelReset()"), self.updateListedFeedItem)
      self.fixPostListUI()

      # Try to scroll to the same post or to the top
      if post and self.ui.posts.model().hasPost(post):
        idx=self.ui.posts.model().indexFromPost(post)
        self.ui.posts.scrollTo(idx, self.ui.posts.EnsureVisible)
        self.ui.posts.setCurrentIndex(idx)
      else:
        self.ui.view.setHtml(renderTemplate('feed.tmpl',feed=feed))
        self.ui.posts.scrollToTop()
      for action in actions:
        action.setEnabled(True)

  def currentFeed(self):
    '''The feed linked to the current index in self.ui.feeds'''
    return self.ui.feeds.model().feedFromIndex(self.ui.feeds.currentIndex())

  def updateFeedItem(self, feed, parents=False, updating=False, can_reopen=False):
    info("Updating item for feed %d", feed.id)
    
    model=self.ui.feeds.model()
    
    if not model:
      return
      
    index=model.indexFromFeed(feed)
    
    if not index.isValid():
      return # Weird, but a feed was added behind our backs or something

    # If we are updating the current feed, update the post list, too
    if self.ui.posts.model() and self.ui.posts.model().feed_id==feed.id:
      # This may call updateFeedItem, so avoid loops
      QtCore.QObject.disconnect(self.ui.posts.model(), QtCore.SIGNAL("modelReset()"), self.updateListedFeedItem)
      pidx=self.ui.posts.currentIndex()
      self.ui.posts.model().initData(update=True)
      self.ui.posts.setCurrentIndex(pidx)
      QtCore.QObject.connect(self.ui.posts.model(), QtCore.SIGNAL("modelReset()"), self.updateListedFeedItem)

    item=self.ui.feeds.model().itemFromIndex(index)
    item2=self.ui.feeds.model().itemFromIndex(self.ui.feeds.model().index(index.row(), 1, index.parent()))
  
    # The calls to setRowHidden cause a change in the column's width! Looks like a Qt bug to me.
    if self.showOnlyUnread:
      if feed.unreadCount()==0 and feed<>self.currentFeed() and feed.parent: 
        # Hide feeds with no unread items
        self.ui.feeds.setRowHidden(item.row(), index.parent(), True)
      else:
        self.ui.feeds.setRowHidden(item.row(), index.parent(), False)
    else:
      if self.ui.feeds.isRowHidden(item.row(), index.parent()):
        self.ui.feeds.setRowHidden(item.row(), index.parent(), False)
    if updating:
      item.setForeground(QtGui.QColor("darkgrey"))
      item2.setForeground(QtGui.QColor("darkgrey"))
    else:
      item.setForeground(QtGui.QColor("black"))
      item2.setForeground(QtGui.QColor("black"))
    item.setText(unicode(feed))
    item2.setText(unicode(feed.unreadCount() or ''))
    item.setToolTip(unicode(feed))
    item2.setToolTip(unicode(feed))
    
    f=item.font()
    if feed.unreadCount():
      f.setBold(True)
    else:
      f.setBold(False)
    item.setFont(f)
    item2.setFont(f)
    
    if parents: # Not by default because it's slow
      # Update all ancestors too, because unread counts and such change
      while feed.parent:
        self.updateFeedItem(feed.parent, True)
        feed=feed.parent
      # And set the systray tooltip to the unread count on root_feed
      self.tray.updateIcon()

  def on_posts_clicked(self, index):
    if index.column()<>0:
      index=self.ui.posts.model().index(index.column(), 0, index.parent())
    post=self.ui.posts.model().postFromIndex(index)
    if post: #post may go away if you changed feeds very quickly
      if post.unread: 
        post.unread=False
        post.feed.curUnread-=1
        elixir.session.flush()
        self.updateFeedItem(post.feed, parents=True)
        self.updatePostItem(post)
      if post.feed.loadFull and post.link:
        # If I pass post.link, it crashes if I click something else quickly
        self.ui.statusBar.showMessage("Opening %s"%post.link)
        self.ui.view.setUrl(QtCore.QUrl(QtCore.QString(post.link)))
      else:
        if self.showingFolder or config.getValue('ui', 'alwaysShowFeed', False) == True:
          self.ui.view.setHtml(renderTemplate('post.tmpl',post=post, showFeed=True))
        else:
          self.ui.view.setHtml(renderTemplate('post.tmpl',post=post, showFeed=False))

  def on_posts_doubleClicked(self, index=None):
    if index==None: return
    item=self.ui.posts.model().itemFromIndex(index)
    if item:
      post=self.ui.posts.model().postFromIndex(index)
      if post and post.link:
        info("Opening %s", post.link)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(post.link))
    
  def on_actionExport_Feeds_triggered(self, i=None):
    if i==None: return
    fname = unicode(QtGui.QFileDialog.getSaveFileName(self, "Save as", os.getcwd(), 
                                              "OPML files (*.opml *.xml)"))
    if fname:
      exportOPML(fname)

  def on_actionImport_Feeds_triggered(self, i=None):
    if i==None: return
    fname = unicode(QtGui.QFileDialog.getOpenFileName(self, "Open OPML file", os.getcwd(), 
                                              "OPML files (*.opml *.xml)"))
    if fname:
      importOPML(fname)
      self.initTree()
      
  def on_actionTechnorati_Top_10_triggered(self, i=None):
    if i==None: return
    if QtGui.QMessageBox.question(None, "Technorati Top 10 - uRSSus", 
       'You are about to import Technorati\'s Top 10 feeds for today.\nClick Yes to confirm.', 
       QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No ) == QtGui.QMessageBox.Yes:
      
      url='http://elliottback.com/tools/top100/technorati-100-to-opml.php'
      data=urlopen(url).read()
      # Create a 'Top 10' folder if there isn't one
      t100=Feed.get_by_or_init(text='Top 10')
      if not t100.parent:
        t100.parent=root_feed
      [h, name]=tempfile.mkstemp()
      tf=os.fdopen(h, 'wb+')
      tf.write(data)
      tf.flush()
      tf.close()
      importOPML(name, parent=t100)
      os.unlink(name)
      self.initTree()
      self.ui.feeds.setCurrentIndex(self.ui.feeds.model().indexFromFeed(t100))
    
      
  def on_actionQuit_triggered(self, i=None):
    if i==None: return
    pos=self.pos()
    config.setValue('ui', 'position', [pos.x(), pos.y()])
    size=self.size()
    config.setValue('ui', 'size', [size.width(), size.height()])
    config.setValue('ui', 'splitters', [self.ui.splitter.sizes(), self.ui.splitter_2.sizes()])
    QtGui.QApplication.instance().quit()
    Post.table.delete(sql.and_(Post.deleted==True, Post.fresh==False)).execute()

  def on_actionMark_Feed_as_Read_triggered(self, i=None):
    if i==None: return

    idx=self.ui.feeds.currentIndex()
    feed=self.ui.feeds.model().feedFromIndex(idx)
    # See if we are displaying the feed using the post list
    if self.ui.posts.model() and self.ui.posts.model().feed_id==feed.id:
      self.ui.posts.model().markRead()
    else: # Mark as read a feed from the tree
      idx=self.ui.feeds.currentIndex()
      feed=self.ui.feeds.model().feedFromIndex(idx)
      if feed:
        feed.markAsRead()
        self.open_feed(idx) # To update all the actions/items

  def on_actionDelete_Feed_triggered(self, i=None):
    if i==None: return
    index=self.ui.feeds.currentIndex()
    item=self.ui.feeds.model().itemFromIndex(index)
    feed=self.ui.feeds.model().feedFromIndex(index)
    if feed:
      info( "Deleting %s", feed)
      if QtGui.QMessageBox.question(None, "Delete Feed - uRSSus", 
           'Are you sure you want to delete "%s"'%feed, 
           QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No ) == QtGui.QMessageBox.Yes:
        parent=feed.parent

        # Clean posts list
        self.ui.posts.setModel(None)
        self.ui.view.setHtml('')

        # Trigger update on parent item
        parent.curUnread=-1
        # I really, really shouldn't have to do this. But it doesn'twork if I don't so...
        parent.children.remove(feed)
        self.updateFeedItem(parent, parents=True)

        # No feed current
        self.ui.feeds.setCurrentIndex(QtCore.QModelIndex())
        feed.delete()
        self.ui.feeds.model().removeRow(index.row(), index.parent())
        elixir.session.flush()
        
  def on_actionOpen_Homepage_triggered(self, i=None):
    if i==None: return
    feed=self.ui.feeds.model().feedFromIndex(self.ui.feeds.currentIndex())
    if feed and feed.htmlUrl:
      info("Opening %s", feed.htmlUrl)
      QtGui.QDesktopServices.openUrl(QtCore.QUrl(feed.htmlUrl))
    
  def on_actionFetch_Feed_triggered(self, i=None):
    if i==None: return
    # Start an immediate update for the current feed
    idx=self.ui.feeds.currentIndex()
    feed=self.ui.feeds.model().feedFromIndex(idx)
    if feed:
      # FIXME: move to out-of-process
      p=processing.Process(target=updateOne, args=(feed, ))
      p.setDaemon(True)
      p.start()
      self.open_feed(idx)
      
  def on_actionFetch_All_Feeds_triggered(self, i=None):
    if i==None: return
    global processes
    # Start an immediate update for all feeds
    statusQueue.put("fetching all feeds")
    p = processing.Process(target=feedUpdater, args=(True, ))
    p.setDaemon(True)
    p.start()
    processes.append(p)
    
  def on_actionAbort_Fetches_triggered(self, i=None):
    if i==None: return
    global processes, statusQueue, feedStatusQueue
    statusQueue.put("Aborting all fetches")
    # stop all processes and restart the background timed fetcher
    for proc in processes:
      proc.terminate()
    processes=[]
    
    # Mark all feeds as not updating
    for feed in Feed.query():
      feedStatusQueue.put([1, feed.id])
    self.updateFeedStatus()
    self.updatesCounter=0
      
  def on_actionNext_Unread_Article_triggered(self, i=None):
    if i==None: return
    info( "Next Unread Article")
    if not self.ui.posts.model(): # Not showing a feed
      self.on_actionNext_Unread_Feed_triggered(True)
      return
    cp=self.getCurrentPost()
    nextIdx=self.ui.posts.model().nextUnreadPostIndex(cp)
    if nextIdx.isValid():
      self.ui.posts.setCurrentIndex(nextIdx)
      self.on_posts_clicked(index=nextIdx)
      return
    else: # Go to next feed
      self.on_actionNext_Unread_Feed_triggered(True)
      
  def on_actionNext_Article_triggered(self, i=None, do_open=True):
    if i==None: return
    info ("Next Article")
    
    cp=self.getCurrentPost()

    # First ask the post list's model
    nextIdx=self.ui.posts.model().nextPostIndex(cp)
    
    if nextIdx.isValid():
      self.ui.posts.setCurrentIndex(nextIdx)
      self.on_posts_clicked(index=nextIdx)
      return
    else: # Go to next feed
      self.on_actionNext_Feed_triggered(True)

  def on_actionPrevious_Unread_Article_triggered(self, i=None):
    if i==None: return
    info("Previous Unread Article")
    if not self.ui.posts.model(): # Not showing a feed
      self.on_actionPrevious_Unread_Feed_triggered(True)
      return

    cp=self.getCurrentPost()
    nextIdx=self.ui.posts.model().previousUnreadPostIndex(cp)
    if nextIdx.isValid():
      self.ui.posts.setCurrentIndex(nextIdx)
      self.on_posts_clicked(index=nextIdx)
      return
    else: # Go to next feed
      self.on_actionPrevious_Unread_Feed_triggered(True)

  def on_actionPrevious_Article_triggered(self, i=None, do_open=True):
    if i==None: return
    info ("Next Article")
    
    cp=self.getCurrentPost()
    # First ask the post list's model
    nextIdx=self.ui.posts.model().previousPostIndex(cp)
    
    if nextIdx.isValid():
      self.ui.posts.setCurrentIndex(nextIdx)
      self.on_posts_clicked(index=nextIdx)
      return
    else: # Go to next feed
      self.on_actionPrevious_Feed_triggered(True)

  def on_actionNext_Feed_triggered(self, i=None):
    if i==None: return
    info("Next Feed")
    feed=self.currentFeed() or root_feed
    nextFeed=feed.nextFeed()
    if nextFeed:
      self.open_feed(self.ui.feeds.model().indexFromFeed(nextFeed))

  def on_actionPrevious_Feed_triggered(self, i=None):
    if i==None: return
    info("Previous Feed")
    f=self.currentFeed()
    if f:
      prevFeed=f.previousFeed()
      if prevFeed and prevFeed<>root_feed: # The root feed has no UI
        self.open_feed(self.ui.feeds.model().indexFromFeed(prevFeed))
    else:
      # No current feed, so what's the meaning of "previous feed"?
      pass
      
  def on_actionNext_Unread_Feed_triggered(self, i=None):
    if i==None: return
    info("Next unread feed")
    f=self.currentFeed() or root_feed
    nextFeed=f.nextUnreadFeed()
    if nextFeed:
      self.open_feed(self.ui.feeds.model().indexFromFeed(nextFeed))

  def on_actionPrevious_Unread_Feed_triggered(self, i=None):
    if i==None: return
    info("Previous unread feed")
    f=self.currentFeed()
    if f:
      prevFeed=f.previousUnreadFeed()
      if prevFeed and prevFeed<>root_feed: # The root feed has no UI
        self.open_feed(self.ui.feeds.model().indexFromFeed(prevFeed))
    else:
      # No current feed, so what's the meaning of "previous unread feed"?
      pass
      
  def on_actionIncrease_Font_Sizes_triggered(self, i=None):
    if i==None: return
    self.ui.view.setTextSizeMultiplier(self.ui.view.textSizeMultiplier()+.2)
    
  def on_actionDecrease_Font_Sizes_triggered(self, i=None):
    if i==None: return
    self.ui.view.setTextSizeMultiplier(self.ui.view.textSizeMultiplier()-.2)

  def on_actionZoom_Reset_triggered(self, i=None):
    if i==None: return
    self.ui.view.setTextSizeMultiplier(1)

class FeedDelegate(QtGui.QItemDelegate):
  def __init__(self, parent=None):
    info("Creating FeedDelegate")
    QtGui.QItemDelegate.__init__(self, parent)
    
class PostDelegate(QtGui.QItemDelegate):
  def __init__(self, parent=None):
    info("Creating PostDelegate")
    QtGui.QItemDelegate.__init__(self, parent)
  
def exportOPML(fname):
  from OPML import Outline, OPML
  from cgi import escape
  def exportSubTree(parent, node):
    if not node.children:
      return
    for feed in node.children:
      co=Outline()
      co['text']=feed.text or ''
      if feed.xmlUrl:
        co['type']='rss'
        co['xmlUrl']=escape(feed.xmlUrl) or ''
        co['htmlUrl']=escape(feed.htmlUrl) or ''
        co['title']=escape(feed.title) or ''
        co['description']=escape(feed.description) or ''
      parent.add_child(co)
      
  opml=OPML()
  root=Outline()
  for feed in root_feed.children:
    exportSubTree(root, feed)
  opml.outlines=root._children
  opml.output(codecs.open(fname, 'w', 'utf-8'))
    
def importOPML(fname, parent=None):
  global root_feed
  if parent == None:
    parent=root_feed

  def importSubTree(parent, node):
    if node.tag<>'outline':
      return # Don't handle
    xu=node.get('xmlUrl')
    if xu:
      # If it's already somewhere, don't duplicate
      f=Feed.get_by(xmlUrl=node.get('xmlUrl'), 
             htmlUrl=node.get('htmlUrl'), 
             )
      if not f:
        f=Feed(xmlUrl=node.get('xmlUrl'), 
             htmlUrl=node.get('htmlUrl'), 
             title=node.get('title'),
             text=node.get('text'), 
             description=node.get('description'), 
             parent=parent
             )
    else: # Let's guess it's a folder
      f=Feed.get_by_or_init(text=node.get('text'), parent=parent)
      for child in node.getchildren():
        importSubTree(f, child)

  from xml.etree import ElementTree
  tree = ElementTree.parse(fname)
  for node in tree.find('//body').getchildren():
    importSubTree(parent, node)
  elixir.session.flush()

    
def main():
  global root_feed
  app=QtGui.QApplication(sys.argv)
  app.setQuitOnLastWindowClosed(False)
  # Not enabled yet, because I need to implement a web app to handle it
  #sys.excepthook = my_excepthook
  window=MainWindow()
    
  if len(sys.argv)>1:
    if sys.argv[1].lower().startswith('http://'):
      window.addFeed(sys.argv[1])
    elif sys.argv[1].lower().endswith('.opml'):
      # Import a OPML file into the DB so we have some data to work with
      importOPML(sys.argv[1], root_feed)
  
  # This will start the background fetcher as a side effect
#  window.on_actionAbort_Fetches_triggered(True)
  window.show()
  sys.exit(app.exec_())
  
