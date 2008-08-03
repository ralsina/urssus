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

import sys, os, time, urlparse, tempfile, codecs
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
    self.feedItems={}
    self.currentFeed=None
    
    self.combinedView=False
    
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
    
    # Timer to mark feeds as busy/updated/whatever
    self.feedStatusTimer=QtCore.QTimer()
    self.feedStatusTimer.setSingleShot(True)
    QtCore.QObject.connect(self.feedStatusTimer, QtCore.SIGNAL("timeout()"), self.updateFeedStatus)
    self.feedStatusTimer.start(0)
    self.updatesCounter=0

    # Load user preferences
    self.loadPreferences()

    # Tray icon
    self.tray=TrayIcon()
    self.tray.show()
    self.notifiedFeed=None
    QtCore.QObject.connect(self.tray, QtCore.SIGNAL("messageClicked()"), self.notificationClicked)
    QtCore.QObject.connect(self.tray, QtCore.SIGNAL("activated( QSystemTrayIcon::ActivationReason)"), self.trayActivated)
    traymenu=QtGui.QMenu(self)
    traymenu.addAction(self.ui.actionFetch_All_Feeds)
    traymenu.addSeparator()
    traymenu.addAction(self.ui.actionQuit)
    self.tray.setContextMenu(traymenu)
    
    # Add all menu actions to this window, so they still work when
    # the menu bar is hidden (tricky!)
    for action in self.ui.menuBar.actions():
      self.addAction(action)

  def fixPostListUI(self):
    # Fixes for post list UI
    header=self.ui.posts.header()
    header.setStretchLastSection(False)
    header.setResizeMode(0, QtGui.QHeaderView.Stretch)
    header.setResizeMode(1, QtGui.QHeaderView.Fixed)
    header.resizeSection(1, header.fontMetrics().width(' 8888-88-88 ')+4)

  def trayActivated(self, reason=None):
    if reason == None: return
    if reason == self.tray.Trigger:
      self.show()
      self.raise_()
    
  def notificationClicked(self):
    if self.notifiedFeed:
      self.open_feed(self.ui.feeds.model().indexFromItem(self.feedItems[self.notifiedFeed.id]))
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

  def on_actionImport_From_Google_Reader_triggered(self, i=None):
    if i==None: return
    import feedfinder
    
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
          print "You are already subscribed to %s"%xmlUrl
          continue
        f=Feed.get_by(xmlUrl=xmlUrl)
        if not f:
          newFeed=Feed(text=title, title=title, xmlUrl=xmlUrl, parent=folder)
#          newFeed.updateFeedData()
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
      self.updateFeedItem(curPost.feed)

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
      curFeed=self.ui.feeds.model().itemFromIndex(index).feed
    info ("Expiring feed: %s", curFeed)
    curFeed.expire(expunge=True)
    # Update feed display (number of unreads may have changed)
    self.updateFeedItem(curFeed,parents=True)
    # Reopen it because the post list probably changed
    self.open_feed(index)

  def on_actionEdit_Feed_triggered(self, i=None):
    if i==None: return
    index=self.ui.feeds.currentIndex()
    if index.isValid():         
      curFeed=self.ui.feeds.model().itemFromIndex(index).feed
    info ("Editing feed: %s", curFeed)

    editDlg=FeedProperties(curFeed)
    if editDlg.exec_():
      # update feed item
      self.updateFeedItem(curFeed)

  def addFeed(self, url):
    # Use Mark pilgrim / Aaron Swartz's RSS finder module
    # FIXME: make this non-blocking somehow
    import feedfinder
    feed=feedfinder.feed(url)
    if not feed:
      QtGui.QMessageBox.critical(self, "Error - uRSSus", "Can't find a feed wit URL: %s"%url)
      return
    info ("Found feed: %s", feed)
    if Feed.get_by(xmlUrl=feed):
      # Already subscribed
      QtGui.QMessageBox.critical(self, "Error - uRSSus", "You are already subscribed")
      return
    newFeed=Feed(xmlUrl=feed)
    newFeed.updateFeedData()
    
    # Figure out the insertion point
    index=self.ui.feeds.currentIndex()
    if index.isValid():         
      curFeed=self.ui.feeds.model().itemFromIndex(index).feed
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
    self.ui.feeds.setCurrentIndex(self.ui.feeds.model().indexFromItem(self.feedItems[newFeed.id]))
    self.on_actionEdit_Feed_triggered(True)

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
        curFeed=self.itemFromIndex(index).feed
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
      self.ui.feeds.setCurrentIndex(self.ui.feeds.model().indexFromItem(self.feedItems[newFolder.id]))

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

  def findText(self):
    text=unicode(self.searchWidget.ui.text.text())
    if self.searchWidget.ui.matchCase.isChecked():
      self.ui.view.findText(text, QtWebKit.QWebPage.FindCaseSensitively)
    else:  
      self.ui.view.findText(text)

  def findTextReverse(self):
    text=unicode(self.searchWidget.ui.text.text())
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

  def filterPosts(self):
    self.textFilter=unicode(self.filterWidget.ui.filter.text())
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
      if not id in self.feedItems:
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
          sys.exit(1)
      feed=Feed.get_by(id=id)
      if action==0: # Mark as updating
        self.updateFeedItem(feed, updating=True)
        self.updatesCounter+=1
      elif action==1: # Mark as finished updating
        # Force recount after update
        feed.curUnread=-1
        self.updateFeedItem(feed, updating=False, parents=True)
        self.updatesCounter-=1
      elif action==2: # Just update it
        self.updateFeedItem(feed, data[2], can_reopen=True)
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
    self.model=FeedModel()
    self.feedItems={}
    
    # Internal function
    def addSubTree(parent, node):
      nn=QtGui.QStandardItem(unicode(node))
      nn.setToolTip(unicode(node))
      parent.appendRow(nn)
      nn.feed=node
      nn.setData(QtCore.QVariant(node.id), QtCore.Qt.UserRole)
      self.feedItems[node.id]=nn
      self.updateFeedItem(node)
      if node.xmlUrl:
        nn.setIcon(QtGui.QIcon(":/urssus.svg"))
      else:
        nn.setIcon(QtGui.QIcon(":/folder.svg"))
        for child in node.children:
          addSubTree(nn, child)
      return nn
          
    iroot=self.model.invisibleRootItem()
    iroot.feed=root_feed
    self.feedItems[root_feed.id]=iroot
    for root in root_feed.children:
      QtGui.QApplication.instance().processEvents()
      addSubTree(iroot, root)
      
    self.ui.feeds.setModel(self.model)
    for k in self.feedItems:
      i=self.feedItems[k]
      if i.feed.is_open: self.ui.feeds.expand(self.model.indexFromItem(i))


    self.setEnabled(True)
    self.filterWidget.setEnabled(True)
    self.searchWidget.setEnabled(True)
    
  def on_feeds_expanded(self, index):
    feed=self.model.feedFromIndex(index)
    if not feed: return
    feed.is_open=True
    elixir.session.flush()
    
  def on_feeds_collapsed(self, index):
    feed=self.model.feedFromIndex(index)
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
    
  def resortPosts(self):
    info ("Resorting posts")
    cp=self.getCurrentPost()
    self.ui.posts.setCurrentIndex(self.ui.posts.model().indexFromPost(cp))
    self.fixPostListUI()

  def open_feed(self, index):
    if not index.isValid():
      return
    feed=self.ui.feeds.model().feedFromIndex(index)
    if not feed: return
    self.ui.feeds.setCurrentIndex(index)
    self.currentFeed=feed
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
      info("Opening combined")
      if feed.xmlUrl: # A regular feed
        self.posts=Post.query.filter(Post.feed==feed)
      else: # A folder
        self.posts=feed.allPostsQuery()
      # Filter by text according to the contents of self.textFilter
      if self.textFilter:
        self.posts=self.posts.filter(sql.or_(Post.title.like('%%%s%%'%self.textFilter), Post.content.like('%%%s%%'%self.textFilter)))
      if self.statusFilter:
        self.posts=self.posts.filter(self.statusFilter==True)
      # FIXME: find a way to add sorting to the UI for this (not very important)
      self.posts=self.posts.order_by(sql.desc(Post.date)).all()
      self.ui.view.setHtml(renderTemplate(self.combinedTemplate,posts=self.posts))

      for action in actions:
        action.setEnabled(False)

    else: # StandardView / Widescreen View
      info ("Opening in standard view")
      
      # Remember current post ID
      cpid=-1000
      if self.ui.posts.model():
        p=self.ui.posts.model().postFromIndex(self.ui.posts.currentIndex())
        if p: cpid=p.id
     
      self.ui.posts.setModel(PostModel(self.ui.posts, feed, self.textFilter, self.statusFilter))
      self.fixPostListUI()
      QtCore.QObject.connect(self.ui.posts.model(), QtCore.SIGNAL("resorted()"), self.resortPosts)

      for action in actions:
        action.setEnabled(True)

      self.ui.view.setHtml(renderTemplate('feed.tmpl',feed=feed))
      
      # Try to scroll to the same post or to the top
      idx=self.ui.posts.model().indexFromPost(Post.get_by(id=cpid))
      if idx.isValid():
        self.ui.posts.scrollTo(idx, self.ui.posts.EnsureVisible)
        self.ui.posts.setCurrentIndex(idx)
      else:
        self.ui.posts.scrollToTop()


  def updateFeedItem(self, feed, parents=False, updating=False, can_reopen=False):
    info("Updating item for feed %d", feed.id)
    if not feed.id in self.feedItems:
      return
    item=self.feedItems[feed.id]
    # This is very slow when marking folders as read
    # because each children triggers an update of the folder
    # and since the folder is current, that triggers
    # a load in the QWebView and reloading all the folder's items in 
    # the post list, etc, etc
    # That's why we special-case the can_reopen, which only
    # is done after a real update
    if feed==self.currentFeed and can_reopen: #It's open, re_open it
      self.open_feed(self.model.indexFromItem(item))
    # The calls to setRowHidden cause a change in the column's width! Looks like a Qt bug to me.
    if self.showOnlyUnread:
      if feed.unreadCount()==0 and feed<>self.currentFeed: 
        # Hide feeds with no unread items
        self.ui.feeds.setRowHidden(item.row(), self.model.indexFromItem(item.parent()), True)
      else:
        self.ui.feeds.setRowHidden(item.row(), self.model.indexFromItem(item.parent()), False)
    else:
      if self.ui.feeds.isRowHidden(item.row(), self.model.indexFromItem(item.parent())):
        self.ui.feeds.setRowHidden(item.row(), self.model.indexFromItem(item.parent()), False)
    if updating:
      item.setForeground(QtGui.QColor("darkgrey"))
    else:
      item.setForeground(QtGui.QColor("black"))
    item.setText(unicode(feed))
    item.setToolTip(unicode(feed))
    
    f=item.font()
    if feed.unreadCount():
      f.setBold(True)
    else:
      f.setBold(False)
    item.setFont(f)
    
    if parents: # Not by default because it's slow
      # Update all ancestors too, because unread counts and such change
      while feed.parent:
        self.updateFeedItem(feed.parent, True)
        feed=feed.parent
      # And set the systray tooltip to the unread count on root_feed
      uc=root_feed.unreadCount()
      self.tray.setToolTip('%d unread posts'%uc)
      if uc:
        self.tray.setIcon(QtGui.QIcon(':/urssus-unread.svg'))
      else:
        self.tray.setIcon(QtGui.QIcon(':/urssus.svg'))

  def on_posts_clicked(self, index):
    if index.column()<>0:
      index=self.ui.posts.model().index(index.column(), 0, index.parent())
    post=self.ui.posts.model().postFromIndex(index)
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
      self.ui.view.setHtml(renderTemplate('post.tmpl',post=post))

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
    if QtGui.QMessageBox.question(None, "Technorati Top 100 - uRSSus", 
       'You are about to import Technorati\'s Top 100 feeds for today.\nClick Yes to confirm.', 
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
      self.ui.feeds.setCurrentIndex(self.ui.feeds.model().indexFromItem(self.feedItems[t100.id]))
    
      
  def on_actionQuit_triggered(self, i=None):
    if i==None: return
    pos=self.pos()
    config.setValue('ui', 'position', [pos.x(), pos.y()])
    size=self.size()
    config.setValue('ui', 'size', [size.width(), size.height()])
    config.setValue('ui', 'splitters', [self.ui.splitter.sizes(), self.ui.splitter_2.sizes()])
    Post.table.delete(sql.and_(Post.deleted==True, Post.fresh==False)).execute()
    QtGui.QApplication.instance().quit()

  def on_actionMark_Feed_as_Read_triggered(self, i=None):
    if i==None: return
    idx=self.ui.feeds.currentIndex()
    feed=self.ui.feeds.model().feedFromIndex(idx)
    if feed:
      feed.markAsRead()
    self.open_feed(idx) # To update all the actions/items

  def on_actionDelete_Feed_triggered(self, i=None):
    if i==None: return
    index=self.ui.feeds.currentIndex()
    item=self.model.itemFromIndex(index)
    if item and item.feed:
      info( "Deleting %s", item.feed)
      if QtGui.QMessageBox.question(None, "Delete Feed - uRSSus", 
         'Are you sure you want to delete "%s"'%item.feed, 
         QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No ) == QtGui.QMessageBox.Yes:
        parent=item.feed.parent

        # Clean posts list
        self.ui.posts.setModel(None)
        self.ui.view.setHtml('')

        # Trigger update on parent item
        parent.curUnread=-1
        # I really, really shouldn't have to do this. But it doesn'twork if I don't so...
        parent.children.remove(item.feed)
        self.updateFeedItem(parent, parents=True)

        # No feed current
        self.ui.feeds.setCurrentIndex(QtCore.QModelIndex())
        self.currentFeed=None

        del(self.feedItems[item.feed.id])
        item.feed.delete()
        self.ui.feeds.model().removeRow(index.row(), index.parent())
        elixir.session.flush()
        
  def on_actionOpen_Homepage_triggered(self, i=None):
    if i==None: return
    item=self.model.itemFromIndex(self.ui.feeds.currentIndex())
    if item and item.feed and item.feed.htmlUrl:
      info("Opening %s", item.feed.htmlUrl)
      QtGui.QDesktopServices.openUrl(QtCore.QUrl(item.feed.htmlUrl))
    
  def on_actionFetch_Feed_triggered(self, i=None):
    if i==None: return
    # Start an immediate update for the current feed
    item=self.model.itemFromIndex(self.ui.feeds.currentIndex())
    if item and item.feed:
      # FIXME: move to out-of-process
      feedStatusQueue.put([0, item.feed.id])
      item.feed.update()
      feedStatusQueue.put([1, item.feed.id])
      self.open_feed(self.ui.feeds.currentIndex())

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
    for id in self.feedItems:
      feedStatusQueue.put([1, id])
    self.updateFeedStatus()
    self.updatesCounter=0
      
  def on_actionNext_Unread_Article_triggered(self, i=None):
    if i==None: return
    info( "Next Unread Article")
    if not self.currentFeed:
      self.on_actionNext_Unread_Feed_triggered(True)
    post=self.getCurrentPost()
    if not post: 
      post=self.ui.posts.model().posts.first()
      if not post: # No posts in this feed, just go the next unread feed
        self.on_actionNext_Unread_Feed_triggered(True)
        return
    if post.unread: # Quirk, should redo the flow
      nextPost=post
    else:
      nextPost=self.currentFeed.nextUnreadPost(post, self.ui.posts.model().sortOrder(), self.statusFilter, self.textFilter)
    if nextPost:
      nextIndex=self.ui.posts.model().indexFromPost(nextPost)
      self.ui.posts.setCurrentIndex(nextIndex)
      self.on_posts_clicked(index=nextIndex)
    else:
      # At the end of the feed, go to next unread feed
      self.on_actionNext_Unread_Feed_triggered(True)
      
  def on_actionNext_Article_triggered(self, i=None, do_open=True):
    if i==None: return
    info ("Next Article")
    cp=self.getCurrentPost()
    if cp:
      nextPost=self.currentFeed.nextPost(cp, self.ui.posts.model().sortOrder(), 
                                         self.statusFilter, self.textFilter)
    else:
      nextPost=self.ui.posts.model().posts.first()
      if not nextPost:
        # No posts in this feed, just go the next unread feed
        self.on_actionNext_Feed_triggered(True)
        return
    if nextPost:
      nextIndex=self.ui.posts.model().indexFromPost(nextPost)
      self.ui.posts.setCurrentIndex(nextIndex)
      self.on_posts_clicked(index=nextIndex)
    else:
      # At the end of the feed, go to next unread feed
      self.on_actionNext_Feed_triggered(True)

  def on_actionPrevious_Unread_Article_triggered(self, i=None):
    if i==None: return
    info("Previous Unread Article")
    post=self.getCurrentPost()
    if post:
      previousPost=self.currentFeed.previousUnreadPost(post, self.ui.posts.model().sortOrder(), 
                                                       self.statusFilter, self.textFilter)
    # Yuck!
    elif self.ui.posts.model().posts.count(): # Not on a specific post, go to the last unread article
      previousPost=self.ui.posts.model().posts.all()[-1]
      if not previousPost.unread:
        previousPost=self.currentFeed.previousUnreadPost(previousPost, 
                                                         self.ui.posts.model().sortOrder(), 
                                                         self.statusFilter, self.textFilter)
    else:
      previousPost=None
    if previousPost:
      nextIndex=self.ui.posts.model().indexFromPost(previousPost)
      self.ui.posts.setCurrentIndex(nextIndex)
      self.on_posts_clicked(index=nextIndex)
    else:
      # At the beginning of the feed, go to previous feed
      self.on_actionPrevious_Unread_Feed_triggered(True)

  def on_actionPrevious_Article_triggered(self, i=None, do_open=True):
    if i==None: return
    info ("Previous Article")
    post=self.getCurrentPost()
    if post:
      previousPost=self.currentFeed.previousPost(post, self.ui.posts.model().sortOrder(), 
                                                 self.statusFilter, self.textFilter)
    # Yuck!
    elif self.ui.posts.model().posts.count(): # Not on a specific post, go to the last unread article
      previousPost=self.ui.posts.model().posts.all()[-1]
    else:
      previousPost=None
    if previousPost:
      nextIndex=self.ui.posts.model().indexFromPost(previousPost)
      self.ui.posts.setCurrentIndex(nextIndex)
      self.on_posts_clicked(index=nextIndex)
    else:
      # At the beginning of the feed, go to previous feed
      self.on_actionPrevious_Feed_triggered(True)

  def on_actionNext_Unread_Feed_triggered(self, i=None):
    if i==None: return
    info("Next unread feed")
    if self.currentFeed:
      nextFeed=self.currentFeed.nextUnreadFeed()
    else:
      nextFeed=root_feed.nextUnreadFeed()
    if nextFeed:
      self.open_feed(self.ui.feeds.model().indexFromItem(self.feedItems[nextFeed.id]))

  def on_actionNext_Feed_triggered(self, i=None):
    if i==None: return
    info("Next Feed")
    if self.currentFeed:
      nextFeed=self.currentFeed.nextFeed()
    else:
      nextFeed=root_feed.nextFeed()
    if nextFeed:
      self.open_feed(self.ui.feeds.model().indexFromItem(self.feedItems[nextFeed.id]))

  def on_actionPrevious_Feed_triggered(self, i=None):
    if i==None: return
    info("Previous Feed")
    if self.currentFeed:
      prevFeed=self.currentFeed.previousFeed()
      if prevFeed and prevFeed<>root_feed: # The root feed has no UI
        self.open_feed(self.ui.feeds.model().indexFromItem(self.feedItems[prevFeed.id]))
    # No current feed, so what's the meaning of "previous feed"?


  def on_actionPrevious_Unread_Feed_triggered(self, i=None):
    if i==None: return
    if self.currentFeed:
      prevFeed=self.currentFeed.previousUnreadFeed()
      if prevFeed and prevFeed<>root_feed: # The root feed has no UI
        self.open_feed(self.ui.feeds.model().indexFromItem(self.feedItems[prevFeed.id]))
    # No current feed, so what's the meaning of "previous unread feed"?
      
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
        # Add any missing stuff (mainly icons, I guess)
        # Kills performance, though
        # f.updateFeedData()
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
  root_feed=initDB()
  app=QtGui.QApplication(sys.argv)
  app.setQuitOnLastWindowClosed(False)
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
  
if __name__ == "__main__":
  main()
