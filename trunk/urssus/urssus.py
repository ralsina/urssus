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
__session__=session

#try:
#  import psyco
#  psyco.full()
#except ImportError:
#  pass

import sys, os, time, urlparse, tempfile, codecs, traceback
from urllib import urlopen, quote
from datetime import datetime, timedelta
from dbtables import Post, Feed, initDB, unread_feed, starred_feed
import elixir
import sqlalchemy as sql

from htmlentitydefs import name2codepoint as n2cp
import re

# Twitter support
try:
  from twitter import Twitter
except ImportError:
  Twitter=None
from util.tiny import tiny


from feedupdater import feedUpdater

# UI Classes
from PyQt4 import QtGui, QtCore, QtWebKit
from ui.Ui_main import Ui_MainWindow
from ui.Ui_about import Ui_Dialog as UI_AboutDialog
from ui.Ui_filterwidget import Ui_Form as UI_FilterWidget
from ui.Ui_searchwidget import Ui_Form as UI_SearchWidget
from ui.Ui_feed_properties import Ui_Dialog as UI_FeedPropertiesDialog
from ui.Ui_twitterpost import Ui_Dialog as UI_TwitterDialog
from ui.Ui_fancyauth import Ui_Dialog as UI_FancyAuthDialog
from ui.Ui_greaderimport import Ui_Dialog as UI_GReaderDialog
from ui.Ui_bugdialog import Ui_Dialog as UI_BugDialog
from ui.Ui_configdialog import Ui_Dialog as UI_ConfigDialog
from ui.Ui_newfeed import Ui_Dialog as UI_NewFeedDialog

from processdialog import ProcessDialog

from postmodel import *

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

class NewFeedDialog(QtGui.QDialog):
  def __init__(self, parent):
    QtGui.QDialog.__init__(self, parent)
    # Set up the UI from designer
    self.ui=UI_NewFeedDialog()
    self.ui.setupUi(self)
    self.ui.label.setText(self.help[0])
    
  help=['''Enter the URL of the site you want to add as a feed.''', 
        '''Enter keywords to create a customized Google News feed.<p> 
        For example, <i>"premier league"</i> if you are interested in english football.''', 
        '''Enter keywords to create a customized Bloglines Search.<p> 
        For example, <i>"premier league"</i> if you are interested in english football.'''
       ]
    
  def on_feedType_activated(self, index=None):
    if index==None: return
    if type(index) is not int: return
    self.ui.label.setText(self.help[index])

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
      innerpage=QtGui.QFrame()
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
          text.setText(unicode(config.getValue(sectionName, optionName, definition[1])))          
          layout.addWidget(label, row, 0, 1, 1)
          layout.addWidget(text, row, 1, 1, 1)
          self.values[sectionName+'/'+optionName]=[text, lambda(text): unicode(text.text())]

        elif definition[0]=='password':
          label=QtGui.QLabel(optionName+":")
          label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
          text=QtGui.QLineEdit()
          text.setEchoMode(QtGui.QLineEdit.Password)
          text.setText(unicode(config.getValue(sectionName, optionName, definition[1])))          
          layout.addWidget(label, row, 0, 1, 1)
          layout.addWidget(text, row, 1, 1, 1)
          self.values[sectionName+'/'+optionName]=[text, lambda(text): unicode(text.text())]

        help=QtGui.QLabel(definition[2])
        help.setWordWrap(True)
        layout.addWidget(help, row, 2, 1, 1)
        separator=QtGui.QFrame()
        separator.setFrameStyle(QtGui.QFrame.HLine|QtGui.QFrame.Plain)
        layout.addWidget(separator, row+1, 0, 1, 3)
      innerpage.setLayout(layout)
      innerpage.adjustSize()
      page.resize(QtCore.QSize(innerpage.width()+5, page.height()))
      page.setWidget(innerpage)
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
    dlg.ui.report.setText('''<pre>Version: %s\n\n%s</pre>'''%(VERSION, msg))
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
    dlg=FancyAuthDialog(self, 'Twitter', QtGui.QPixmap(':/twitter.svg'))
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
    
class FancyAuthDialog(QtGui.QDialog):
  def __init__(self, parent, service_name, icon):
    QtGui.QDialog.__init__(self, parent)
    # Set up the UI from designer
    self.ui=UI_FancyAuthDialog()
    self.ui.setupUi(self)
    self.setWindowTitle('%s Authentication - uRSSus'%service_name)
    self.ui.label.setText('Please enter your %s username and password'%service_name)
    self.ui.icon.setPixmap(icon or QtGui.QPixmap(':/urssus.svg'))

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
    try:
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
      elixir.session.commit()
    except:
      elixir.session.rollback()
    QtGui.QDialog.accept(self)

class MainWindow(QtGui.QMainWindow):
  def __init__(self):
    QtGui.QMainWindow.__init__(self)

    # Internal indexes
    self.combinedView=False
    self.showingFolder=False
    self.pendingFeedUpdates={}
    
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
    # Make status filter persistent
    self.filterWidget.ui.statusCombo.setCurrentIndex(config.getValue('ui', 'statusFilter', 0))
        
    # Search widget
    self.ui.searchBar.hide()
    self.searchWidget=SearchWidget()
    self.ui.searchBar.addWidget(self.searchWidget)
    QtCore.QObject.connect(self.searchWidget.ui.next, QtCore.SIGNAL("clicked()"), self.findText)
    QtCore.QObject.connect(self.searchWidget.ui.previous, QtCore.SIGNAL("clicked()"), self.findTextReverse)
    QtCore.QObject.connect(self.searchWidget.ui.close, QtCore.SIGNAL("clicked()"), self.ui.searchBar.hide)
    QtCore.QObject.connect(self.searchWidget.ui.close, QtCore.SIGNAL("clicked()"), self.ui.view.setFocus)
    # Completion with history
    self.searchHistory=[]
    self.filterHistory=[]

    # Set some properties of the Web view
    page=self.ui.view.page()
    if not config.getValue('options', 'followLinksInUrssus', False):
      page.setLinkDelegationPolicy(page.DelegateAllLinks)
    self.ui.view.setFocus(QtCore.Qt.TabFocusReason)
    QtWebKit.QWebSettings.globalSettings().setUserStyleSheetUrl(QtCore.QUrl(cssFile))
    QtWebKit.QWebSettings.globalSettings().setAttribute(QtWebKit.QWebSettings.PluginsEnabled, True)    
    QtWebKit.QWebSettings.globalSettings().setWebGraphic(QtWebKit.QWebSettings.MissingImageGraphic, QtGui.QPixmap(':/file_broken.svg').scaledToHeight(24))
    copy_action=self.ui.view.page().action(QtWebKit.QWebPage.Copy)
    self.ui.view.page().action(QtWebKit.QWebPage.OpenLinkInNewWindow).setVisible(False)
    copy_action.setIcon(QtGui.QIcon(':/editcopy.svg'))
    self.ui.menu_Edit.insertAction(self.ui.actionFind, copy_action )
    self.ui.menu_Edit.insertSeparator(self.ui.actionFind)
    self.ui.view.setFocus(QtCore.Qt.TabFocusReason)

    # Set sorting for post list
    column,order=config.getValue('ui','postSorting',[2,QtCore.Qt.DescendingOrder])
    order=[QtCore.Qt.AscendingOrder,QtCore.Qt.DescendingOrder][order]
    self.ui.posts.sortByColumn(column, order)
    # Set custom context menu hook in post list header
    header=self.ui.posts.header()
    header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    QtCore.QObject.connect(header, QtCore.SIGNAL("customContextMenuRequested(const QPoint)"), self.postHeaderContextMenu)
    QtCore.QObject.connect(header, QtCore.SIGNAL("sectionMoved ( int, int, int)"), 
                                   self.savePostColumnPosition)

    # Timer to trigger status bar updates
    self.statusTimer=QtCore.QTimer()
    self.statusTimer.setSingleShot(True)
    QtCore.QObject.connect(self.statusTimer, QtCore.SIGNAL("timeout()"), self.updateStatusBar)
    self.statusTimer.start(1000)

    
    # Load user preferences
    self.loadPreferences()

    # Tray icon
    self.tray=TrayIcon()
    self.tray.show()
    self.notifiedFeed=None
    QtCore.QObject.connect(self.tray, QtCore.SIGNAL("messageClicked()"), self.notificationClicked)
    QtCore.QObject.connect(self.tray, QtCore.SIGNAL("activated( QSystemTrayIcon::ActivationReason)"), self.trayActivated)
    self.tray.updateIcon()
    self.setWindowIcon(self.tray.icon())
    traymenu=QtGui.QMenu(self)
    traymenu.addAction(self.ui.actionFetch_All_Feeds)
    traymenu.addSeparator()
    traymenu.addAction(self.ui.actionQuit)
    self.tray.setContextMenu(traymenu)
    
    # Add all menu actions to this window, so they still work when
    # the menu bar is hidden (tricky!)
    for action in self.ui.menuBar.actions():
      self.addAction(action)


    # Fill with feed data
    self.initTree()
    if self.showOnlyUnread:
      self.ui.actionShow_Only_Unread_Feeds.setChecked(self.showOnlyUnread)
      self.on_actionShow_Only_Unread_Feeds_triggered(self.showOnlyUnread)

    # Timer to mark feeds as busy/updated/whatever
    self.feedStatusTimer=QtCore.QTimer()
    self.feedStatusTimer.setSingleShot(True)
    QtCore.QObject.connect(self.feedStatusTimer, QtCore.SIGNAL("timeout()"), self.updateFeedStatus)
    self.feedStatusTimer.start(3000)
    # Start the background feedupdater
    feedUpdateQueue.put([1])

  def fixPostListUI(self):
    # Fixes for post list UI
    widths=config.getValue('ui', 'postColumnWidths', [])
    header=self.ui.posts.header()
    header.setStretchLastSection(False)
    header.setResizeMode(0, QtGui.QHeaderView.Fixed)
    header.resizeSection(0, 24)
    header.setResizeMode(1, QtGui.QHeaderView.Stretch)
    header.setResizeMode(2, QtGui.QHeaderView.Fixed)
    header.resizeSection(2, header.fontMetrics().width(' 88/88/8888 8888:88:88 ')+4)
    header.setResizeMode(3, QtGui.QHeaderView.Interactive)
    if widths:
      header.resizeSection(3, widths[3])
    self.loadPostColumnPosition()
    starred, feed, date=config.getValue('ui', 'visiblePostColumns', [True, False, True])
    self.ui.actionShowStarredColumn.setChecked(starred)
    self.ui.actionShowFeedColumn.setChecked(feed)
    self.ui.actionShowDateColumn.setChecked(date)
    if starred:
      header.showSection(0)
    else:
      header.hideSection(0)
    if feed:
      header.showSection(3)
    else:
      header.hideSection(3)
    if date:
      header.showSection(2)
    else:
      header.hideSection(2)
        
  def savePostSectionSizes(self, *args):
    ws=[max(24, self.ui.posts.header().sectionSize(i)) for i in [0, 1, 2, 3]]
    if ws==[24, 24, 24, 24]: return #Header is not initialized yet
    config.setValue('ui', 'postColumnWidths',ws)

  def fixFeedListUI(self):
    # Fixes for feed list UI
    header=self.ui.feedTree.header()
    header.setStretchLastSection(False)
    header.setResizeMode(0, QtGui.QHeaderView.Stretch)
    header.setResizeMode(1, QtGui.QHeaderView.Fixed)
    header.resizeSection(1, header.fontMetrics().width(' Unread ')+4)
    
  def savePostColumns(self):
    config.setValue('ui', 'visiblePostColumns', [self.ui.actionShowStarredColumn.isChecked(), 
                                                 self.ui.actionShowFeedColumn.isChecked(), 
                                                 self.ui.actionShowDateColumn.isChecked()])

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
      self.open_feed2(self.ui.feedTree.itemFromFeed(self.notifiedFeed))
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

    self.showOnlyUnread=config.getValue('ui', 'showOnlyUnreadFeeds', False)
    
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

  def loadPostColumnPosition(self):
    positions=config.getValue('ui', 'postColumnPosition', [0, 1, 2, 3, 4])
    colPos=zip([0, 1, 2, 3, 4], positions)
    colPos.sort(key=operator.itemgetter(1))
    header=self.ui.posts.header()
    # Gack!
    for logical, visual in colPos:
      header.moveSection(header.visualIndex(logical), visual)
      
  def savePostColumnPosition(self, logical, vfrom, vto):
    header=self.ui.posts.header()
    pos=[ header.visualIndex(logical) for logical in xrange(0, 5)]
    config.setValue('ui', 'postColumnPosition', pos)
    
  def getCurrentPost(self):
    index=self.ui.posts.currentIndex()
    if not index.isValid() or not self.ui.posts.model():
      return None
    return self.ui.posts.model().postFromIndex(index)

  def on_actionSync_Bookmarks_To_Web_triggered(self, i=None):
    if i==None: return
    # Start with del.icio.us, we'll make it configurable later
    u=config.getValue('del.icio.us', 'username', '')
    p=config.getValue('del.icio.us', 'password', '')
    if not u or not p:
      dlg=FancyAuthDialog(self, 'Del.icio.us', None)
      dlg.ui.username.setText(unicode(u))
      dlg.ui.password.setText(unicode(p))
      if dlg.exec_():
        u=unicode(dlg.ui.username.text())
        p=unicode(dlg.ui.password.text())
        if dlg.ui.saveit.isChecked():
          config.setValue('del.icio.us', 'username',u)
          config.setValue('del.icio.us', 'password',p)
      else:
        return
    import util.pydelicious as api
    api.USER_AGENT='uRSSus/%s +http://urssus.googlecode.com/'%VERSION
    bookmarks=api.get_all(u, p)['posts']
#    d={'update': '2008-08-11T00:57:05Z', 'total': '46', 'posts': [{'extended': '', 'hash': 'd96b01349453284448b84bb84a3404ad', 'description': 'Use the Google Chart API to create charts for your web applications', 'others': '-1', 'tag': '', 'href': 'http://ajaxian.com/archives/use-the-google-chart-api-to-create-charts-for-your-web-applications', 'time': '2007-12-07T16:32:13Z'}, {'extended': 'Del.icio.us ...  chocolate... makes sense', 'hash': 'cc00400414425788b357b25f3cbef09f', 'description': 'Installation on Chocolate Laptop', 'others': '-1', 'tag': 'linux fun', 'href': 'http://en.opensuse.org/Installation_on_Chocolate_Laptop', 'time': '2007-11-29T20:55:17Z'}, {'extended': '', 'hash': '357b3ce293d5b504d6426dd2346d23ab', 'description': 'Religious scholars mull Flying Spaghetti Monster', 'others': '-1', 'tag': 'religion', 'href': 'http://edition.cnn.com/2007/LIVING/personal/11/16/flying.spaghettimonster.ap/index.html', 'time': '2007-11-16T20:12:34Z'}, {'extended': 'Almost makes me want to really learn Java', 'hash': '28335a003b9db66a0d4cccc7f61cfd17', 'description': 'About Android', 'others': '-1', 'tag': 'programming java android', 'href': 'http://www.betaversion.org/~stefano/linotype/news/110/', 'time': '2007-11-13T16:17:46Z'}, {'extended': 'I really should have made those custom t-shirts saying "RMS called me evil".', 'hash': 'fab148d73ea94cada3875a94d6a58b04', 'description': 'RMS is still a social moron.', 'others': '-1', 'tag': '', 'href': 'http://edward.oconnor.cx/2005/04/rms', 'time': '2007-08-12T01:06:51Z'}, {'extended': '', 'hash': 'abd0c0cccefac0c0cb1fbe1d366f53fa', 'description': 'Blows your mind. Then carefully patches it together seamlessly.', 'others': '-1', 'tag': 'api graphics programming software', 'href': 'http://graphics.cs.cmu.edu/projects/scene-completion/', 'time': '2007-08-09T17:54:49Z'}, {'extended': '', 'hash': 'cf57e5b554f53ab86d957ac16ef0ef02', 'description': 'On how Borges wrote Fight Club', 'others': '-1', 'tag': 'literature borges writing', 'href': 'http://www.sunclipse.org/?p=220#more-220', 'time': '2007-08-05T21:29:18Z'}, {'extended': '', 'hash': '25b071ac1b257aee3928548018888552', 'description': 'Christopher Hitchens: nuts, but a kind of nuts I like.', 'others': '-1', 'tag': 'politics religion', 'href': 'http://www.slate.com/id/2171371/fr/flyout', 'time': '2007-07-30T23:20:50Z'}, {'extended': 'Neat lua language stuff.', 'hash': 'd5a6c5e7ffbefde4ff30a2065b543d39', 'description': 'Bootstraping a forth in 40 lines of Lua code', 'others': '-1', 'tag': 'programming lua forth', 'href': 'http://angg.twu.net/miniforth-article.html', 'time': '2007-07-29T21:55:30Z'}, {'extended': "It's always good to read a little Feynman.", 'hash': '2984b8f3f48de76a46a7e3b389e45eb3', 'description': 'Judging Books by Their Covers, by\nRichard P. Feynman', 'others': '-1', 'tag': 'science education', 'href': 'http://www.textbookleague.org/103feyn.htm', 'time': '2007-07-05T15:14:33Z'}, {'extended': "Having been a sqlite user since 2002 (or earlier?) , I love that it's getting all the atention now that Google/Adobe/Apple use it. It's a great product!", 'hash': 'a88e57f7f9c1e0ef3de78a02bf56bd2c', 'description': 'Interview with Dr. Hipp (The SQLite author)', 'others': '-1', 'tag': 'programming', 'href': 'http://technology.guardian.co.uk/weekly/story/0,,2107239,00.html?gusrc=rss&feed=20', 'time': '2007-06-21T11:56:33Z'}, {'extended': 'I have been learning forth and other stack languages for a couple of weeks, and it turns out Python uses a stack language for pickle!', 'hash': 'efaaf8312ea06524d2931b0960ec737c', 'description': 'Pickle: An interesting stack language', 'others': '-1', 'tag': 'python programming', 'href': 'http://peadrop.com/blog/2007/06/18/pickle-an-interesting-stack-language/', 'time': '2007-06-19T00:47:48Z'}, {'extended': 'A ridiculously tiny WM', 'hash': '24dbed3cd449615f65fecd607c9bd974', 'description': 'TinyWM', 'others': '-1', 'tag': 'programming C python', 'href': 'http://incise.org/index.cgi/TinyWM', 'time': '2007-06-06T14:43:40Z'}, {'extended': 'Seriously useful.', 'hash': 'b1ed5d24e0ec323dcb9292e896ab960a', 'description': 'Python LRU cache decorator', 'others': '-1', 'tag': 'programming python', 'href': 'http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/498245', 'time': '2007-06-03T18:10:37Z'}, {'extended': 'Interesting language.', 'hash': '5c3b56b92cf80b8bf5638fee439f2829', 'description': 'Converge', 'others': '-1', 'tag': 'programming', 'href': 'http://convergepl.org/about.html', 'time': '2007-06-02T23:07:30Z'}, {'extended': 'A sort of C++-ish language that compiles to C. Net features. Sadly, it seems dead.', 'hash': '99573083f347d8d41b5e6e5ab14ef1f1', 'description': 'LightWeight C++', 'others': '-1', 'tag': 'programming c++ C', 'href': 'http://students.ceid.upatras.gr/~sxanth/lwc/index.html', 'time': '2007-05-31T13:14:31Z'}, {'extended': 'Add journaled IO to your apps with very little effort.', 'hash': 'eedc8c98aaadf2f27ade1c058ff7e045', 'description': 'LIBJio: Journaled I/O library', 'others': '-1', 'tag': 'programming C python transactions', 'href': 'http://users.auriga.wearlab.de/~alb/libjio/', 'time': '2007-05-31T13:13:32Z'}, {'extended': "It's not that hard!... once they tell you how to do it.", 'hash': '74d550f779dc857b2b33e0f824f30af3', 'description': 'How to write a spelling corrector', 'others': '-1', 'tag': 'programming', 'href': 'http://www.norvig.com/spell-correct.html', 'time': '2007-05-31T13:06:09Z'}, {'extended': 'Neat python stuff.', 'hash': '96a59c7c5e623353d87950567ce8fefc', 'description': 'Producer/comsumer with multitask', 'others': '-1', 'tag': 'python programming', 'href': 'http://www.oluyede.org/blog/2007/05/29/producerconsumer-with-multitask-library/', 'time': '2007-05-30T16:13:19Z'}, {'extended': "I might take colubrid out of bartleblog and use this as embedded web server for previews.... (if that made no sense to you, don't worry)", 'hash': 'b525a0bb159c641aa1b3f3220dad14cf', 'description': 'Roll your own server in 50 lines of code', 'others': '-1', 'tag': 'python programming', 'href': 'http://muharem.wordpress.com/2007/05/29/roll-your-own-server-in-50-lines-of-code/', 'time': '2007-05-30T12:31:14Z'}, {'extended': 'Now, how unixy would it be to have a vi as the editor in your web forms? I say very.', 'hash': '17235cce8ab10c2da13cd51bc3d7afe8', 'description': 'Vi implemented in javascript.', 'others': '-1', 'tag': 'unix ajax programming javascript', 'href': 'http://ajaxian.com/archives/jsvi-you-love-vi-you-love-javascript-now-you-have-both', 'time': '2007-05-30T12:02:08Z'}, {'extended': "Cool graphic toy app. I wish someone would write one similar for KDE, but it's not my field, really. Should be a useful tool to learn programming in a real language.", 'hash': '0e613dd51f837f8b8726b1a9bf2f4481', 'description': 'NodeBox', 'others': '-1', 'tag': 'programming python graphics software', 'href': 'http://nodebox.net/code/index.php/Home', 'time': '2007-05-26T15:40:34Z'}, {'extended': 'Python cooperative multitasking using generators', 'hash': 'cb8f68dba3188f0e65ef0c26a6267ec9', 'description': 'multitask', 'others': '-1', 'tag': 'python programming', 'href': 'http://programming.reddit.com/goto?id=1tje3', 'time': '2007-05-26T01:10:21Z'}, {'extended': 'Now with math!', 'hash': '45356d156b6925a7de7cb825fccf6f3a', 'description': 'How much of a jerk do you have to be to oppose immigration?', 'others': '-1', 'tag': 'math society economics', 'href': 'http://notsneaky.blogspot.com/2007/05/how-much-of-jerk-do-you-have-to-be-to.html', 'time': '2007-05-25T12:20:34Z'}, {'extended': '', 'hash': '61256535076d34cb1e740d36c80ac921', 'description': 'ESR is soooo annoying', 'others': '-1', 'tag': 'linux esr', 'href': 'https://www.redhat.com/archives/fedora-devel-list/2007-February/msg01051.html', 'time': '2007-05-24T02:21:04Z'}, {'extended': 'Instant is a Python module that allows for instant inlining of C and C++ code in Python.', 'hash': 'dedab5604054db2303beb76fed3576ac', 'description': 'Instant', 'others': '-1', 'tag': 'programming python C c++', 'href': 'http://www.fenics.org/wiki/Instant', 'time': '2007-05-22T21:53:28Z'}, {'extended': "And the worst part is that I think I know exactly where this is. It's not really top secret, though. Just a little secret.", 'hash': '43a00971f5107b4ef73d3dd45d7f11c4', 'description': 'A DailyWTF in Argentina!', 'others': '-1', 'tag': 'argentina sysadmin', 'href': 'http://worsethanfailure.com/Articles/The-Indexer.aspx', 'time': '2007-05-22T20:51:17Z'}, {'extended': "As a former college teacher, one of the saddest things I've read in a while.", 'hash': '6e84152b0a23e6883963ae08671700cf', 'description': 'A dream lay dying', 'others': '-1', 'tag': '', 'href': 'http://reddit.com/goto?rss=true&id=1shwt', 'time': '2007-05-22T01:27:10Z'}, {'extended': 'So, take 02:03 and watch this one.', 'hash': '674da70a45628312b8f875f3064f43fb', 'description': 'You should always have time for Penn & Teller', 'others': '-1', 'tag': 'art', 'href': 'http://www.youtube.com/watch?v=un1pNtmYguA&eurl=http%3A%2F%2Fwww.videosift.com%2Fvideo%2FPenn-Teller-Shadows-Trick-Amazing', 'time': '2007-05-22T01:06:29Z'}, {'extended': '', 'hash': '7841db7bc260939b635aa1f061cedebf', 'description': 'Amazingly bad APIs', 'others': '-1', 'tag': 'programming python java api', 'href': 'http://paulbuchheit.blogspot.com/2007/05/amazingly-bad-apis.html', 'time': '2007-05-21T17:00:31Z'}, {'extended': 'Really.', 'hash': '6c215a6123127e8dad20d028d93df54c', 'description': "Pacman's skull", 'others': '-1', 'tag': 'art', 'href': 'http://reddit.com/goto?rss=true&id=1sbzu', 'time': '2007-05-21T14:13:39Z'}, {'extended': 'Silly, true.', 'hash': '567d42a4fdbbd254e03dc520f6f46239', 'description': 'LOLcats', 'others': '-1', 'tag': 'art', 'href': 'http://www.slate.com/id/2166338/slideshow/2166369/fs/0//entry/2166370/', 'time': '2007-05-21T14:01:46Z'}, {'extended': 'It turns out they are pretty much ok.', 'hash': '24584c342eaf25ec10043eee649bc7ab', 'description': 'The kids these days', 'others': '-1', 'tag': '', 'href': 'http://www.reason.com/news/show/120293.html', 'time': '2007-05-21T13:54:39Z'}, {'extended': 'The better RPM package manager.', 'hash': '40bf3bd62f06c75f96344200a12187b3', 'description': 'Smart 0.51 released', 'others': '-1', 'tag': 'linux sysadmin rpm', 'href': 'http://labix.org/smart', 'time': '2007-05-21T04:07:47Z'}, {'extended': 'Mako is the nicest template engine for python, AFAIK', 'hash': 'e0c09fa6d41163a715b1e8205dbf8480', 'description': 'Exploring Mako', 'others': '-1', 'tag': 'programming python', 'href': 'http://beachcoder.wordpress.com/2007/05/11/exploring-mako/', 'time': '2007-05-20T22:45:07Z'}, {'extended': "And it looks so much better, too. I hope more projects used ReST. It produces great-looking docs and it's simpler than most alternatives.", 'hash': '82e69de185f5bfe2bcb81aa2535672e3', 'description': 'Python Documentation in ReST', 'others': '-1', 'tag': 'python docs ReST', 'href': 'http://www.voidspace.org.uk/python/weblog/arch_d7_2007_05_19.shtml#e722', 'time': '2007-05-20T12:17:37Z'}, {'extended': "I like it. I have my schedule in my phone, since it's what I always have with me, but it has no todo app. This one is good enough.", 'hash': '23639cfaf42ad043b051cf6d3ae4505c', 'description': 'QTodo: todo list manager', 'others': '-1', 'tag': 'qt todo', 'href': 'http://qtodo.berlios.de/', 'time': '2007-05-18T20:13:26Z'}, {'extended': 'They are indeed nice fonts.', 'hash': '474fb28635527e58590ec447f87ac388', 'description': '25 Best Free Quality Fonts', 'others': '-1', 'tag': 'sysadmin', 'href': 'http://www.alvit.de/blog/article/20-best-license-free-official-fonts', 'time': '2007-05-18T19:25:13Z'}, {'extended': 'Awesome.', 'hash': 'd7b7a52d13566bb37e4dc4e431e887da', 'description': 'Lejo Theater & Animatie', 'others': '-1', 'tag': 'art', 'href': 'http://www.lejo.nu/', 'time': '2007-05-18T19:24:15Z'}, {'extended': 'I always thought he was a better draughtsman than painter', 'hash': '41c2151cb7ac89e03dd355a06ad51308', 'description': 'The Drawings of Leonardo da Vinci', 'others': '-1', 'tag': 'art', 'href': 'http://www.drawingsofleonardo.org/', 'time': '2007-05-18T19:22:18Z'}, {'extended': 'So, it seems Enterprise is designed by idiots.', 'hash': '891f56269b4e385799f56d5b51993ac2', 'description': 'Engineering and Star Trek', 'others': '-1', 'tag': 'scifi science engineering', 'href': 'http://www.stardestroyer.net/Empire/Essays/Engineering.html', 'time': '2007-05-17T20:36:54Z'}, {'extended': 'Cool blog/ajax/webpage gadgetry from google', 'hash': '455f23d8b4eee81d088e2bb38ab38c0a', 'description': 'AJAX Feed API: Blogroll and Slideshow Controls', 'others': '-1', 'tag': 'programming ajax', 'href': 'http://ajaxian.com/archives/ajax-feed-api-blogroll-and-slideshow-controls', 'time': '2007-05-17T16:48:50Z'}, {'extended': '', 'hash': '52a51a04139de8cc17de53eb1d68d0ec', 'description': 'Generate dependency graphs from Python code.', 'others': '-1', 'tag': 'programming python', 'href': 'http://furius.ca/snakefood/', 'time': '2007-05-17T01:09:59Z'}, {'extended': '', 'hash': '44ea22173772bca0701ad0f8b204a086', 'description': 'A world covered in hot ice. Cool. Or rather. Hot.', 'others': '-1', 'tag': 'science astronomy', 'href': 'http://www.sciam.com/article.cfm?alias=hot-ice-may-cover-recentl&chanId=sa003&modsrc=reuters', 'time': '2007-05-16T22:47:56Z'}, {'extended': 'And has a huge advantage: you can forcefully kill a process.', 'hash': '2f0f0ffea584524b2b1656450748f2bd', 'description': 'Package for using processes which mimics the threading module', 'others': '-1', 'tag': 'python programming', 'href': 'http://cheeseshop.python.org/pypi/processing', 'time': '2007-05-15T23:02:03Z'}, {'extended': 'Compilers and related tools for many, many languages.', 'hash': '6f24c7aaa32705beeb319cbe21e4fa07', 'description': 'Catalog of free compilers', 'others': '-1', 'tag': 'programming compiler', 'href': 'http://www.idiom.com/free-compilers/', 'time': '2007-05-15T14:32:34Z'}], 'user': 'ralsina', 'tag': ''}
#    bookmarks=d['posts']
    hrefs=set([p['href'] for p in bookmarks])
    # Now fetch all our bookmarked posts
    for post in Post.query.filter(Post.important==True):
      if not post.link in hrefs:
        api.add(u, p, post.link, post.title, tags = "", extended = "", dt = "", replace="no")


  def on_actionShowStarredColumn_triggered(self, checked=None):
    if checked==None:return
    header=self.ui.posts.header()      
    if checked:
      header.showSection(0)
    else:
      header.hideSection(0)
    self.savePostColumns()

  def on_actionShowFeedColumn_triggered(self, checked=None):
    if checked==None:return
    header=self.ui.posts.header()      
    if checked:
      header.showSection(3)
    else:
      header.hideSection(3)
    self.savePostColumns()

  def on_actionShowDateColumn_triggered(self, checked=None):
    if checked==None:return
    header=self.ui.posts.header()      
    if checked:
      header.showSection(2)
    else:
      header.hideSection(2)
    self.savePostColumns()

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
      import util.GoogleReader.reader as gr
      reader=gr.GoogleReader()
      reader.identify(unicode(dlg.ui.username.text()), 
                      unicode(dlg.ui.password.text()))
      if not reader.login():
        QtGui.QMessageBox.critical(self, 'Error - uRSSus', 'Error logging into Google Reader' )
      else:
        subs=reader.get_subscription_list()['subscriptions']
        for sub in subs:
          title=sub['title']
          id=sub['id'] # Something like feed/http://lambda-the-ultimate.org/rss.xml 
          if id.startswith('feed/'):
            xmlUrl=id[5:]
          else:
            # Don't know how to handle it
            error(str(sub))
            continue
          # Treat the first category's label as a folder name.
          cats=sub['categories']
          if cats:
            fname=cats[0]['label']
          # So, with a xmlUrl and a fname, we can just create the feed
          # See if we have the folder
          try:
            folder=Feed.get_by_or_init(parent=root_feed, text=fname, xmlUrl=None)
            if Feed.get_by(xmlUrl=xmlUrl):
              # Already subscribed
              # FIXME: implement progress reports
              error("You are already subscribed to %s", xmlUrl)
              continue
            f=Feed.get_by(xmlUrl=xmlUrl)
            if not f:
              newFeed=Feed(text=title, title=title, xmlUrl=xmlUrl, parent=folder)
            elixir.session.commit()
          except:
            elixir.session.rollback()
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
    # FIXME: the article doesn't disappear (not a regression because of feedTree)
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    info ("Deleting post: %s"%curPost)
    if QtGui.QMessageBox.question(None, "Delete Article - uRSSus", 
        'Are you sure you want to delete "%s"'%curPost, 
        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No ) == QtGui.QMessageBox.Yes:
      try:
        curPost.deleted=True
        self.updatePostItem(curPost)
        elixir.session.commit()
      except:
        elixir.session.rollback()
      self.open_feed2(self.ui.feedTree.currentItem())

  def on_actionMark_as_Read_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    if curPost.unread:
      debug ("Marking as read post: %s"%curPost)
      try:
        curPost.unread=False
        curPost.feed.curUnread-=1 
        elixir.session.commit()
      except:
        elixir.session.rollback()
      self.updatePostItem(curPost)
      self.queueFeedUpdate(curPost.feed)

  def queueFeedUpdate(self, feed, parents=True):
    feedStatusQueue.put([1, feed.id])
    if parents:
      p=feed.parent
      while p:
        feedStatusQueue.put([1, p.id])
        p=p.parent

  def updatePostItem(self, post):
    self.ui.posts.model().updateItem(post)

  def on_actionMark_as_Unread_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    if not curPost.unread:
      info ("Marking as unread post: %s", curPost)
      try:
        curPost.unread=True
        curPost.feed.curUnread+=1
        elixir.session.commit()
      except:
        elixir.session.rollback()
      self.updatePostItem(curPost)
      self.queueFeedUpdate(curPost.feed)

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
    debug ("Marking as important post: %s"%curPost)
    if not curPost.important:
      try:
        curPost.important=True
        elixir.session.commit()
      except:
        elixir.session.rollback()
    self.updatePostItem(curPost)

  def on_actionRemove_Important_Mark_triggered(self, i=None):
    # FIXME: handle selections
    if i==None: return
    curPost=self.getCurrentPost()
    if not curPost: return
    debug ("Marking as not important post: %s"%curPost)
    if curPost.important:
      try:
        curPost.important=False
        elixir.session.commit()
      except:
        elixir.session.rollback()
    self.updatePostItem(curPost)

  def postHeaderContextMenu(self, pos):
    if pos==None: return
    menu=QtGui.QMenu()
    menu.addAction(self.ui.actionShowStarredColumn)
    menu.addAction(self.ui.actionShowDateColumn)
    menu.addAction(self.ui.actionShowFeedColumn)
    menu.exec_(QtGui.QCursor.pos())

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

  def on_feedTree_customContextMenuRequested(self, pos=None):
    if pos==None: return
    
    feed=self.ui.feedTree.itemAt(pos).feed
    if feed:      
      menu=QtGui.QMenu()
      # Common actions
      menu.addAction(self.ui.actionMark_Feed_as_Read)
      menu.addSeparator()
      menu.addAction(self.ui.actionFetch_Feed)
      menu.addSeparator()
      if feed.xmlUrl: # Regular Feed
        menu.addAction(self.ui.actionOpen_Homepage)
        menu.addSeparator()
        menu.addAction(self.ui.actionEdit_Feed)
        menu.addAction(self.ui.actionExpire_Feed)
        menu.addAction(self.ui.actionDelete_Feed)
      else: # Folder
        menu.addAction(self.ui.actionAdd_Feed)
        menu.addAction(self.ui.actionNew_Folder)
        menu.addSeparator()
        menu.addAction(self.ui.actionEdit_Feed)
        menu.addAction(self.ui.actionDelete_Feed)
      menu.exec_(QtGui.QCursor.pos())

  def on_actionExpire_Feed_triggered(self, i=None):
    if i==None: return
    item=self.ui.feedTree.currentItem()
    if not item: return
    curFeed=item.feed
    debug("Expiring feed: %s"%curFeed)
    curFeed.expire(expunge=True)
    # Update feed display (number of unreads may have changed)
    # This would trigger a merge with the post list, but since
    # the user actively expired it, we force a new postmodel
    # and reopen the feed
    self.ui.posts.setModel(None)
    self.open_feed2(item)
    self.queueFeedUpdate(curFeed)

  def on_actionEdit_Feed_triggered(self, i=None):
    if i==None: return
    item=self.ui.feedTree.currentItem()
    if not item: return
    curFeed=item.feed
    if not curFeed.xmlUrl:
      self.ui.feedTree.editItem(item)
      return
    debug("Editing feed: %s"%curFeed)

    editDlg=FeedProperties(curFeed)
    editDlg.exec_()
    self.open_feed2(item)

  def addFeed(self, url):
    # Use Mark pilgrim / Aaron Swartz's RSS finder module
    
    # This takes a few seconds, because we need to fetch the feed and parse it
    # So, start a background process, show a dialog, and make the user wait
    dlg=ProcessDialog(self, callable=self.realAddFeed, args=[url, ])
    if dlg.exec_():
      # Retrieve the feed
      newFeed=Feed.get_by(id=dlg.result)
      # Figure out the insertion point
      item=self.ui.feedTree.currentItem()
      if item:         
        curFeed=item.feed
      else:
        curFeed=root_feed
      try:
        # if curFeed is a feed, add as sibling
        if curFeed.xmlUrl:
          newFeed.parent=curFeed.parent
        # if curFeed is a folder, add as child
        else:
          newFeed.parent=curFeed
        elixir.session.commit()
      except:
        elixir.session.rollback()
      self.initTree()
      item=self.ui.feedTree.itemFromFeed(newFeed)
      self.ui.feedTree.setCurrentItem(item)
      self.open_feed2(item)
      self.on_actionEdit_Feed_triggered(True)
    
  def realAddFeed(self, url, output):
    _info   = lambda(msg): output.put([0, msg])
    _error  = lambda(msg): output.put([2, msg])
    _return = lambda(msg): output.put([100, msg])
      
    import util.feedfinder as feedfinder
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
    try:
      newFeed=Feed(xmlUrl=feed)
      elixir.session.commit()
    except:
      elixir.session.rollback()
    _info ('Fetching feed information')
    # To show it on the tree
    newFeed.update()
    _info ('done')
    _return (newFeed.id)
    

  def on_actionAdd_Feed_triggered(self, i=None):
    if i==None: return
    # Ask for feed URL
    dlg=NewFeedDialog(self)
    if dlg.exec_():
      idx=dlg.ui.feedType.currentIndex()
      data=unicode(dlg.ui.data.text())
      if idx==1: # Google News Feed
        data='http://news.google.com/news?q=%s&output=atom'%quote(data)
      elif idx==2: # Ask.com Feed
        data='http://ask.bloglines.com/search?q=%s&ql=&format=rss'%quote(data)
      self.addFeed(unicode(data))

  def on_actionNew_Folder_triggered(self, i=None):
    if i==None: return
    # Ask for folder name
    [name, ok]=QtGui.QInputDialog.getText(self, "Add Folder - uRSSus", "&Folder name:")
    if ok:
      newFolder=Feed(text=unicode(name))
      # Figure out the insertion point      
      item=self.ui.feedTree.currentItem()
      if not item:
        item=self.feedTree.root_item
      curFeed=item.feed
      # if curFeed is a feed, add as sibling
      try:
        if curFeed.xmlUrl:
          newFolder.parent=curFeed.parent
        # if curFeed is a folder, add as child
        else:
          newFolder.parent=curFeed
        elixir.session.commit()
      except:
        elixir.session.rollback()
      self.initTree()

  def on_actionShow_Only_Unread_Feeds_triggered(self, checked=None):
    if checked==None: return
    self.showOnlyUnread=checked
    config.setValue('ui', 'showOnlyUnreadFeeds', checked)
    for feed in Feed.query.filter(Feed.xmlUrl<>None):
      if feed.unreadCount()==0:
        self.queueFeedUpdate(feed)
  
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
      debug("No filtering by status")
      self.statusFilter=None
    elif status==1: # Unread
      debug("Filtering by status: unread")
      self.statusFilter=Post.unread
    elif status==2: # Important
      debug("Filtering by status: important")
      self.statusFilter=Post.important
    self.open_feed2(self.ui.feedTree.currentItem())
    config.setValue('ui', 'statusFilter', status)
      
  def unFilterPosts(self):
    self.textFilter=''
    self.filterWidget.ui.filter.setText('')
    self.filterWidget.ui.statusCombo.setCurrentIndex(0)
    info("Text filter removed")
    self.open_feed2(self.ui.feedTree.currentItem())
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
    debug("Text filter set to: %s"%self.textFilter)
    self.open_feed2(self.ui.feedTree.currentItem())
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
      try:
        if command=='read':
          post.unread=False
        elif command=='unread':
          post.unread=True
        elif command=='important':
          post.important=True
        elif command=='unimportant':
          post.important=False
        elixir.session.commit()
      except:
        elixir.session.rollback()
      post.feed.curUnread=-1
      self.queueFeedUpdate(post.feed)
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
    info("updateFeedStatus queue length: %d"%len(self.pendingFeedUpdates))
    try:
      while not feedStatusQueue.empty():
        # The idea: this function should never fail.
        # But, if we do, we keep our last attempted update in 
        # memory, and we'll restart it the next try.
        data=feedStatusQueue.get()
        [action, id] = data[:2]
        debug("updateFeedStatus: %d %d"%(action, id))
        
        # FIXME: make this more elegant
        # These are not really feed updates
        if action in [4, 5, 6]:
          if action==4: # Add new feed
            self.addFeed(id)
          elif action==5: #OPML to import
            importOPML(id, root_feed)
            self.initTree()
          elif action==6: #Just pop
            self.show()
            self.raise_()
          else:
            error( "id %s not in the tree"%id)
        # We collapse all updates for a feed, and keep the last one
        else:
          self.pendingFeedUpdates[id]=data
      
      for id in self.pendingFeedUpdates:
        if not self.pendingFeedUpdates[id]: continue
        [action, id]=self.pendingFeedUpdates[id]
        feed=Feed.get_by(id=id)
        if not feed: # Maybe it got deleted while queued
          self.pendingFeedUpdates[id]=None
          continue
        if action==0: # Mark as updating
          self.updateFeedItem(feed)
        else: # Mark as finished updating
          # Force recount after update
          feed.curUnread=-1
          feed.unreadCount()
          self.updateFeedItem(feed)
          if feed.notify and len(data)>2: # Systray notification
            self.notifiedFeed=feed
            self.tray.showMessage("New Articles", "%d new articles in %s"%(data[2], feed.text) )
        # We got this far, that means it's not pending anymore!
        self.pendingFeedUpdates[id]=None
      # We got this far, that means nothing is pending anymore!
      self.pendingFeedUpdates={}
    except:
      # FIXME: handle errors better
      traceback.print_exc(10)
      error("FIX error handling in updateFeedStatus already!")
    self.feedStatusTimer.start(2000)

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

  def updateTree(self, feed):
    self.initTree()
    item=self.ui.feedTree.itemFromFeed(feed)
    self.ui.feedTree.setCurrentItem(item)
    self.open_feed2(item)

  def initTree(self):
    self.setEnabled(False)
    self.ui.feedTree.initTree()
    self.fixFeedListUI()
    self.setEnabled(True)
    self.filterWidget.setEnabled(True)
    self.searchWidget.setEnabled(True)
    
  def on_feedTree_itemExpanded(self, item):
    feed=item.feed
    try:
      feed.is_open=True
      elixir.session.commit()
    except:
      elixir.session.rollback()
    
  def on_feedTree_itemCollapsed(self, item):
    feed=item.feed
    try:
      feed.is_open=False
      elixir.session.commit()
    except:
      elixir.session.rollback()

  def on_feedTree_itemClicked(self, item, column=None):
    if not item: return
    feed=item.feed
    self.open_feed2(item)
    if not self.combinedView:
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
      self.ui.splitter_2.insertWidget(0, self.ui.feedTree)
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
      self.ui.splitter_2.insertWidget(0, self.ui.feedTree)
      self.ui.splitter_2.insertWidget(1, self.ui.splitter)
      self.ui.splitter.show()
      self.ui.splitter_2.show()
      
    self.ui.posts.show()
    self.ui.actionNormal_View.setEnabled(False)
    self.ui.actionCombined_View.setEnabled(True)
    self.ui.actionFancy_View.setEnabled(True)
    self.ui.actionWidescreen_View.setEnabled(True)
    self.open_feed2(self.ui.feedTree.currentItem())
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
      self.ui.splitter.insertWidget(0, self.ui.feedTree)
      self.ui.splitter.insertWidget(1, self.ui.posts)
      self.ui.splitter_2.insertWidget(0, self.ui.splitter)
      self.ui.splitter_2.insertWidget(1, self.ui.view_container)
      self.ui.splitter.show()
      self.ui.splitter_2.show()
    else:
      self.ui.centralWidget.layout().addWidget(self.ui.splitter) 
      self.ui.centralWidget.layout().addWidget(self.ui.splitter_2) 
      self.ui.splitter_2.insertWidget(0, self.ui.feedTree)
      self.ui.splitter_2.insertWidget(1, self.ui.posts)
      self.ui.splitter_2.insertWidget(2, self.ui.view_container)
      self.ui.splitter.hide()
      self.ui.splitter_2.show()

    self.ui.posts.show()
    self.ui.actionNormal_View.setEnabled(True)
    self.ui.actionCombined_View.setEnabled(True)
    self.ui.actionFancy_View.setEnabled(True)
    self.ui.actionWidescreen_View.setEnabled(False)
    self.open_feed2(self.ui.feedTree.currentItem())
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
      self.ui.splitter.insertWidget(0, self.ui.feedTree)
      self.ui.splitter.insertWidget(1, self.ui.view_container)
      self.ui.splitter.show()
      self.ui.splitter_2.hide()
    else:
      self.ui.centralWidget.layout().addWidget(self.ui.splitter) 
      self.ui.centralWidget.layout().addWidget(self.ui.splitter_2)
      self.ui.splitter_2.insertWidget(0, self.ui.feedTree)
      self.ui.splitter_2.insertWidget(1, self.ui.view_container)
      self.ui.splitter.hide()
      self.ui.splitter_2.show()
        
    self.ui.posts.hide()
    self.ui.actionNormal_View.setEnabled(True)
    self.ui.actionCombined_View.setEnabled(False)
    self.ui.actionFancy_View.setEnabled(True)
    self.ui.actionWidescreen_View.setEnabled(True)
    self.open_feed2(self.ui.feedTree.currentItem())
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
    self.queueFeedUpdate(feed)

  def open_feed2(self, item):
    if not item: return
    feed=item.feed
    unreadCount=feed.unreadCount()
        
    if feed.xmlUrl:
      self.showingFolder=False
    else:
      self.showingFolder=True
    
    self.ui.feedTree.setCurrentFeed(feed)
    # Scroll the feeds view so this feed is visible
    self.ui.feedTree.scrollToItem(item)

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
        self.posts=self.posts.filter(sql.or_(Post.title.like('%%%s%%'%self.textFilter), 
                                             Post.content.like('%%%s%%'%self.textFilter), 
                                             Post.tags.like('%%%s%%'%self.textFilter)))
      if self.statusFilter:
        self.posts=self.posts.filter(self.statusFilter==True)
      # FIXME: find a way to add sorting to the UI for this (not very important)
      self.posts=self.posts.order_by(sql.desc(Post.date)).all()
      self.ui.view.setHtml(renderTemplate(self.combinedTemplate, posts=self.posts, showFeed=showFeedInPosts))

      for action in actions:
        action.setEnabled(False)

    else: # StandardView / Widescreen View
      info ("Opening in standard view")
      # FIXME: There must be a better place to call this
      self.savePostSectionSizes()
      
      model=self.ui.posts.model()

      # Remember current post
      if self.ui.posts.model():
        post=self.ui.posts.model().postFromIndex(self.ui.posts.currentIndex())
      else:
        post=None

      # The == are weird because sqlalchemy reimplementes the == operator for
      # model.statusFilter
      if model and model.feed_id==feed.id and \
            str(model.textFilter)==str(self.textFilter) and \
            str(model.statusFilter)==str(self.statusFilter):
        self.ui.posts.model().initData(update=True)
      else:
        self.ui.posts.setModel(PostModel(self.ui.posts, feed, self.textFilter, self.statusFilter))
        QtCore.QObject.connect(self.ui.posts.model(), QtCore.SIGNAL("modelReset()"), self.updateListedFeedItem)
        QtCore.QObject.connect(self.ui.posts.model(), QtCore.SIGNAL("dropped(PyQt_PyObject)"), self.updateTree)
        header=self.ui.posts.header()
        # Don't show feed column yet
        header.hideSection(3)
      self.fixPostListUI()

      # Try to scroll to the same post or to the top
      
      self.updatePostList()
      
      for action in actions:
        action.setEnabled(True)

  def currentFeed(self):
    '''The feed linked to the current item in self.ui.feedTree'''
    item=self.ui.feedTree.currentItem()
    if item:
      return item.feed
    return None

  def updatePostList(self):
    # This may call updateFeedItem, so avoid loops
    QtCore.QObject.disconnect(self.ui.posts.model(), QtCore.SIGNAL("modelReset()"), self.updateListedFeedItem)
    cp=self.ui.posts.model().postFromIndex(self.ui.posts.currentIndex())
    self.ui.posts.model().initData(update=True)
    if cp:
      idx=self.ui.posts.model().indexFromPost(cp)
      self.ui.posts.setCurrentIndex(idx)
      self.ui.posts.scrollTo(idx, self.ui.posts.EnsureVisible)
    else:
      self.ui.posts.scrollToTop()
    QtCore.QObject.connect(self.ui.posts.model(), QtCore.SIGNAL("modelReset()"), self.updateListedFeedItem)

  def updateFeedItem(self, feed):
    info("Updating item for feed %d"%feed.id)
    
    item=self.ui.feedTree.itemFromFeed(feed)
    
    if not item:
      return # Weird, but a feed was added behind our backs or something
    unreadCount=feed.unreadCount()
    # If we are updating the current feed, update the post list, too
    if self.ui.posts.model() and self.ui.posts.model().feed_id==feed.id:
      self.updatePostList()
  
    if self.showOnlyUnread:
      if unreadCount==0 and feed<>self.currentFeed() and feed.xmlUrl: 
        # Hide feeds with no unread items
        item.setHidden(True)
      else:
        item.setHidden(False)
    else:
      if item.parent() and item.parent().isHidden():
        item.parent().setHidden(False)
    if feed.updating:
      item.setForeground(0, QtGui.QColor("darkgrey"))
      item.setForeground(1, QtGui.QColor("darkgrey"))
    else:
      item.setForeground(0, QtGui.QColor("black"))
      item.setForeground(1, QtGui.QColor("black"))
    self.ui.feedTree.update(self.ui.feedTree.indexFromItem(item, 0))
    self.ui.feedTree.update(self.ui.feedTree.indexFromItem(item, 1))
        
    if feed==root_feed:
      # And set the unread count in the "unread items" item
      unread_feed.curUnread=-1
      self.updateFeedItem(unread_feed)
      # And set the systray tooltip to the unread count on root_feed
      self.tray.updateIcon()
      self.setWindowIcon(self.tray.icon())
#    self.updateFeedItem(starred_feed)
  
  def on_posts_clicked(self, index):
    post=self.ui.posts.model().postFromIndex(index)
    if post: #post may go away if you changed feeds very quickly
      if post.feed.loadFull and post.link:
        # If I pass post.link, it crashes if I click something else quickly
        self.ui.statusBar.showMessage("Opening %s"%post.link)
        self.ui.view.setUrl(QtCore.QUrl(QtCore.QString(post.link)))
      else:
        showFeed = self.showingFolder or config.getValue('ui', 'alwaysShowFeed', False) == True
        if not self.showingFolder:
          post.content = decode_htmlentities(post.content)
        self.ui.view.setHtml(renderTemplate('post.tmpl',post=post, showFeed=showFeed))
      QtGui.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents, 1000)
      upUnread=False
      upImportant=False
      upFeed=False
      try:
        if index.column()==0: # Star icon
          post.important= not post.important
          upImportant=True
        if post.unread: 
          post.unread=False
          post.feed.curUnread-=1
          upUnread=True
          upFeed=True
        elixir.session.commit()
      except:
        elixir.session.rollback()

      if upUnread or upImportant:
          self.updatePostItem(post)
      if upFeed:
          self.queueFeedUpdate(post.feed)
 
  def on_posts_doubleClicked(self, index=None):
    if index==None: return
    item=self.ui.posts.model().itemFromIndex(index)
    if item:
      post=self.ui.posts.model().postFromIndex(index)
      if post and post.link:
        debug("Opening %s"%post.link)
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
      self.ui.feedTree.setCurrentItem(self.ui.feedTree.itemFromFeed(t100))
    
      
  def on_actionQuit_triggered(self, i=None):
    if i==None: return
    pos=self.pos()
    config.setValue('ui', 'position', [pos.x(), pos.y()])
    size=self.size()
    config.setValue('ui', 'size', [size.width(), size.height()])
    config.setValue('ui', 'splitters', [self.ui.splitter.sizes(), self.ui.splitter_2.sizes()])
    self.savePostSectionSizes()
    try:
      Post.table.delete(sql.and_(Post.deleted==True, Post.fresh==False)).execute()
      elixir.session.commit()
    except:
      error("Failed to commit deletion on quit")
      elixir.session.rollback()
    QtGui.QApplication.instance().quit()

  @RetryOnDBError
  def on_actionMark_Feed_as_Read_triggered(self, i=None):
    if i==None: return

    item=self.ui.feedTree.currentItem()
    feed=item.feed
    # See if we are displaying the feed using the post list
    if self.ui.posts.model() and self.ui.posts.model().feed_id==feed.id:
      self.ui.posts.model().markRead()
      self.queueFeedUpdate(feed)
    else: # Mark as read a feed from the tree
      item=self.ui.feedTree.currentItem()
      if item:
        feed=item.feed
        feed.markAsRead()
        self.open_feed2(item) # To update all the actions/items

  @RetryOnDBError
  def on_actionDelete_Feed_triggered(self, i=None):
    if i==None: return
    item=self.ui.feedTree.currentItem()
    if not item: return
    feed=item.feed
    # FIXME: generalize 'don't delete'
    # Don't delete root_feed
    if feed == root_feed:
      return
    if feed:
      info( "Deleting %s", feed)
      if QtGui.QMessageBox.question(None, "Delete Feed - uRSSus", 
           'Are you sure you want to delete "%s"'%feed, 
           QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No ) == QtGui.QMessageBox.Yes:
             
        # Clean posts list
        self.ui.posts.setModel(None)
        self.ui.view.setHtml('')
             
        try:
          if feed.parent:
            parent=feed.parent
            # Trigger update on parent item
            parent.curUnread=-1
            # I really, really shouldn't have to do this. But it doesn'twork if I don't so...
            parent.removeChild(feed)
          feed.delete()
          elixir.session.commit()
        except:
          elixir.session.rollback()
        # No feed current
        self.ui.feedTree.setCurrentItem(None)
        item.parent().removeChild(item)
        self.queueFeedUpdate(parent)
        
  def on_actionOpen_Homepage_triggered(self, i=None):
    if i==None: return
    feed=None
    item=self.ui.feedTree.currentItem()
    if item:
      feed=item.feed
    if feed and feed.htmlUrl:
      info("Opening %s", feed.htmlUrl)
      QtGui.QDesktopServices.openUrl(QtCore.QUrl(feed.htmlUrl))
    
  def on_actionFetch_Feed_triggered(self, i=None):
    if i==None: return
    # Start an immediate update for the current feed
    item=self.ui.feedTree.currentItem()
    if not item: return
    feed=item.feed
    feedUpdateQueue.put(feed)
      
  def on_actionFetch_All_Feeds_triggered(self, i=None):
    if i==None: return
    global processes
    # Start an immediate update for all feeds
    statusQueue.put("fetching all feeds")
    feedUpdateQueue.put(root_feed)
    
  def on_actionAbort_Fetches_triggered(self, i=None):
    if i==None: return
    global processes, statusQueue, feedStatusQueue
    statusQueue.put("Aborting all fetches")
    #FIXME: reimplement
     
  @RetryOnDBError
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
      
  @RetryOnDBError
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

  @RetryOnDBError
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

  @RetryOnDBError
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

  @RetryOnDBError
  def on_actionNext_Feed_triggered(self, i=None):
    if i==None: return
    info("Next Feed")
    feed=self.currentFeed() or root_feed
    nextFeed=feed.nextFeed(self.ui.feedTree.order_by())
    if nextFeed:
      self.open_feed2(self.ui.feedTree.itemFromFeed(nextFeed))

  @RetryOnDBError
  def on_actionPrevious_Feed_triggered(self, i=None):
    if i==None: return
    info("Previous Feed")
    f=self.currentFeed()
    if f:
      prevFeed=f.previousFeed(self.ui.feedTree.order_by())
      if prevFeed and prevFeed<>root_feed: # The root feed has no UI
        self.open_feed2(self.ui.feedTree.itemFromFeed(prevFeed))
    else:
      # No current feed, so what's the meaning of "previous feed"?
      pass
      
  @RetryOnDBError
  def on_actionNext_Unread_Feed_triggered(self, i=None):
    if i==None: return
    info("Next unread feed")
    f=self.currentFeed() or root_feed
    nextFeed=f.nextUnreadFeed(self.ui.feedTree.order_by())
    if nextFeed:
      self.open_feed2(self.ui.feedTree.itemFromFeed(nextFeed))

  @RetryOnDBError
  def on_actionPrevious_Unread_Feed_triggered(self, i=None):
    if i==None: return
    info("Previous unread feed")
    f=self.currentFeed()
    if f:
      prevFeed=f.previousUnreadFeed(self.ui.feedTree.order_by())
      if prevFeed and prevFeed<>root_feed: # The root feed has no UI
        self.open_feed2(self.ui.feedTree.itemFromFeed(prevFeed))
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
  
def exportOPML(fname):
  from util.OPML import Outline, OPML
  import cgi
  def exportSubTree(parent, node):
    children=node.getChildren()
    if not children:
      return
    for feed in children:
      co=Outline()
      co['text']=feed.text
      if feed.xmlUrl:
        co['type']='rss'
        co['xmlUrl']=feed.xmlUrl
        co['htmlUrl']=feed.htmlUrl or ''
        co['title']=cgi.escape(feed.title or '')
        co['description']=cgi.escape(feed.description or '')
      parent.add_child(co)
      
  opml=OPML()
  root=Outline()
  for feed in root_feed.getChildren():
    exportSubTree(root, feed)
  opml.outlines=root._children
  f=open(fname, 'wb')
  f.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n')
  # FIXME: error with unicode characters in feed elements :-(
  opml.output(f)
  
    
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
        try:
          f=Feed(xmlUrl=node.get('xmlUrl'), 
               htmlUrl=node.get('htmlUrl'), 
               title=node.get('title'),
               text=node.get('text'), 
               description=node.get('description'), 
               parent=parent
               )
          elixir.session.commit()
        except:
          elixir.session.rollback()

    else: # Let's guess it's a folder
      try:
        f=Feed.get_by_or_init(text=node.get('text'), parent=parent)
        elixir.session.commit()
      except:
        elixir.session.rollback()

      for child in node.getchildren():
        importSubTree(f, child)

  from xml.etree import ElementTree
  tree = ElementTree.parse(fname)
  for node in tree.find('//body').getchildren():
    importSubTree(parent, node)

# TODO: move substitute_entity and decode_htmlentities to utils module
def substitute_entity(match):
  ent = match.group(2)
  if match.group(1) == "#":
    return unichr(int(ent))
  else:
    cp = n2cp.get(ent)
    if cp:
      return unichr(cp)
    else:
      return match.group()

def decode_htmlentities(string):
  entity_re = re.compile("&(#?)(\d{1,5}|\w{1,8});")
  return entity_re.subn(substitute_entity, string)[0]


import dbus 
import dbus.service
from dbus.mainloop import qt

class UrssusServer(dbus.service.Object):
  def __init__(self, window, bus_name, object_path="/uRSSus"):
    dbus.service.Object.__init__(self, bus_name, object_path)
    self.window=window
    
  @dbus.service.method("org.urssus.interface")
  def AddFeed(self, url):
      self.window.addFeed(url)

  @dbus.service.method("org.urssus.interface")
  def show(self):
    self.window.show()
    self.window.raise_()

  @dbus.service.method("org.urssus.interface")
  def importOPML(self, fname):
    importOPML(fname)


def main():
  global root_feed
  
  app=QtGui.QApplication(sys.argv)
  app.setQuitOnLastWindowClosed(False)

  # Not enabled yet, because I need to implement a web app to handle it
  if config.getValue('options','showDebugDialog', False):
    sys.excepthook = my_excepthook
  window=MainWindow()

  mainloop = qt.DBusQtMainLoop(set_as_default=True)
  session_bus = dbus.SessionBus()
  name = dbus.service.BusName("org.urssus.service", bus=session_bus)
  object = UrssusServer(window,name)
    
  if len(sys.argv)>1:
    if sys.argv[1].lower().startswith('http://'):
      window.addFeed(sys.argv[1])
    elif sys.argv[1].lower().endswith('.opml'):
      # Import a OPML file into the DB so we have some data to work with
      importOPML(sys.argv[1], root_feed)
  
  if not config.getValue('ui', 'startOnTray', False):
    window.show()
  sys.exit(app.exec_())
  
