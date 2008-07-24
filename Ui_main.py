# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/ralsina/Desktop/proyectos/urssus/main.ui'
#
# Created: Thu Jul 24 15:14:41 2008
#      by: PyQt4 UI code generator 4.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800,600)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/urssus.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        MainWindow.setWindowIcon(icon)
        MainWindow.setIconSize(QtCore.QSize(24,24))
        MainWindow.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.centralWidget = QtGui.QWidget(MainWindow)
        self.centralWidget.setGeometry(QtCore.QRect(0,70,800,506))
        self.centralWidget.setObjectName("centralWidget")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.centralWidget)
        self.verticalLayout_2.setMargin(1)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.splitter_2 = QtGui.QSplitter(self.centralWidget)
        self.splitter_2.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_2.setObjectName("splitter_2")
        self.feeds = QtGui.QTreeView(self.splitter_2)
        self.feeds.setFocusPolicy(QtCore.Qt.NoFocus)
        self.feeds.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.feeds.setFrameShape(QtGui.QFrame.Panel)
        self.feeds.setFrameShadow(QtGui.QFrame.Plain)
        self.feeds.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.feeds.setAlternatingRowColors(True)
        self.feeds.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.feeds.setIndentation(20)
        self.feeds.setRootIsDecorated(True)
        self.feeds.setUniformRowHeights(True)
        self.feeds.setAnimated(True)
        self.feeds.setAllColumnsShowFocus(True)
        self.feeds.setHeaderHidden(True)
        self.feeds.setObjectName("feeds")
        self.splitter = QtGui.QSplitter(self.splitter_2)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setObjectName("splitter")
        self.posts = QtGui.QTreeView(self.splitter)
        self.posts.setFocusPolicy(QtCore.Qt.NoFocus)
        self.posts.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.posts.setFrameShape(QtGui.QFrame.Panel)
        self.posts.setFrameShadow(QtGui.QFrame.Plain)
        self.posts.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.posts.setAlternatingRowColors(True)
        self.posts.setRootIsDecorated(False)
        self.posts.setUniformRowHeights(True)
        self.posts.setItemsExpandable(False)
        self.posts.setSortingEnabled(True)
        self.posts.setAnimated(True)
        self.posts.setAllColumnsShowFocus(True)
        self.posts.setExpandsOnDoubleClick(False)
        self.posts.setObjectName("posts")
        self.frame = QtGui.QFrame(self.splitter)
        self.frame.setFrameShape(QtGui.QFrame.Panel)
        self.frame.setFrameShadow(QtGui.QFrame.Plain)
        self.frame.setObjectName("frame")
        self.verticalLayout = QtGui.QVBoxLayout(self.frame)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.view = QtWebKit.QWebView(self.frame)
        self.view.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.view.setUrl(QtCore.QUrl("about:blank"))
        self.view.setObjectName("view")
        self.verticalLayout.addWidget(self.view)
        self.verticalLayout_2.addWidget(self.splitter_2)
        MainWindow.setCentralWidget(self.centralWidget)
        self.toolBar = QtGui.QToolBar(MainWindow)
        self.toolBar.setGeometry(QtCore.QRect(0,31,155,39))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/urssus.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.toolBar.setWindowIcon(icon)
        self.toolBar.setIconSize(QtCore.QSize(24,24))
        self.toolBar.setObjectName("toolBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea,self.toolBar)
        self.menuBar = QtGui.QMenuBar(MainWindow)
        self.menuBar.setGeometry(QtCore.QRect(0,0,800,31))
        self.menuBar.setObjectName("menuBar")
        self.menuFeed = QtGui.QMenu(self.menuBar)
        self.menuFeed.setObjectName("menuFeed")
        self.menu_File = QtGui.QMenu(self.menuBar)
        self.menu_File.setObjectName("menu_File")
        self.menu_Go = QtGui.QMenu(self.menuBar)
        self.menu_Go.setObjectName("menu_Go")
        self.menuHelp = QtGui.QMenu(self.menuBar)
        self.menuHelp.setObjectName("menuHelp")
        self.menu_View = QtGui.QMenu(self.menuBar)
        self.menu_View.setObjectName("menu_View")
        self.menu_Edit = QtGui.QMenu(self.menuBar)
        self.menu_Edit.setObjectName("menu_Edit")
        self.menuArticle = QtGui.QMenu(self.menuBar)
        self.menuArticle.setObjectName("menuArticle")
        MainWindow.setMenuBar(self.menuBar)
        self.statusBar = QtGui.QStatusBar(MainWindow)
        self.statusBar.setGeometry(QtCore.QRect(0,576,800,24))
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)
        self.filterBar = QtGui.QToolBar(MainWindow)
        self.filterBar.setGeometry(QtCore.QRect(155,31,645,39))
        self.filterBar.setObjectName("filterBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea,self.filterBar)
        self.actionFetch_Feed = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/1downarrow.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionFetch_Feed.setIcon(icon)
        self.actionFetch_Feed.setObjectName("actionFetch_Feed")
        self.actionFetch_All_Feeds = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/2downarrow.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionFetch_All_Feeds.setIcon(icon)
        self.actionFetch_All_Feeds.setObjectName("actionFetch_All_Feeds")
        self.actionAbort_Fetches = QtGui.QAction(MainWindow)
        self.actionAbort_Fetches.setEnabled(False)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/stop.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionAbort_Fetches.setIcon(icon)
        self.actionAbort_Fetches.setObjectName("actionAbort_Fetches")
        self.actionMark_Feed_as_Read = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/apply.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionMark_Feed_as_Read.setIcon(icon)
        self.actionMark_Feed_as_Read.setObjectName("actionMark_Feed_as_Read")
        self.actionImport_Feeds = QtGui.QAction(MainWindow)
        self.actionImport_Feeds.setObjectName("actionImport_Feeds")
        self.actionExport_Feeds = QtGui.QAction(MainWindow)
        self.actionExport_Feeds.setObjectName("actionExport_Feeds")
        self.actionQuit = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/exit.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionQuit.setIcon(icon)
        self.actionQuit.setObjectName("actionQuit")
        self.actionNext_Article = QtGui.QAction(MainWindow)
        self.actionNext_Article.setObjectName("actionNext_Article")
        self.actionNext_Unread_Article = QtGui.QAction(MainWindow)
        self.actionNext_Unread_Article.setObjectName("actionNext_Unread_Article")
        self.actionNext_Feed = QtGui.QAction(MainWindow)
        self.actionNext_Feed.setObjectName("actionNext_Feed")
        self.actionNext_Unread_Feed = QtGui.QAction(MainWindow)
        self.actionNext_Unread_Feed.setObjectName("actionNext_Unread_Feed")
        self.actionAbout_uRSSus = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/urssus.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionAbout_uRSSus.setIcon(icon)
        self.actionAbout_uRSSus.setObjectName("actionAbout_uRSSus")
        self.actionIncrease_Font_Sizes = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/viewmag+.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionIncrease_Font_Sizes.setIcon(icon)
        self.actionIncrease_Font_Sizes.setObjectName("actionIncrease_Font_Sizes")
        self.actionDecrease_Font_Sizes = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/viewmag-.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionDecrease_Font_Sizes.setIcon(icon)
        self.actionDecrease_Font_Sizes.setObjectName("actionDecrease_Font_Sizes")
        self.actionStatus_Bar = QtGui.QAction(MainWindow)
        self.actionStatus_Bar.setCheckable(True)
        self.actionStatus_Bar.setChecked(True)
        self.actionStatus_Bar.setObjectName("actionStatus_Bar")
        self.actionPrevious_Feed = QtGui.QAction(MainWindow)
        self.actionPrevious_Feed.setObjectName("actionPrevious_Feed")
        self.actionPrevious_Unread_Feed = QtGui.QAction(MainWindow)
        self.actionPrevious_Unread_Feed.setObjectName("actionPrevious_Unread_Feed")
        self.actionPrevious_Article = QtGui.QAction(MainWindow)
        self.actionPrevious_Article.setObjectName("actionPrevious_Article")
        self.actionPrevious_Unread_Article = QtGui.QAction(MainWindow)
        self.actionPrevious_Unread_Article.setObjectName("actionPrevious_Unread_Article")
        self.actionFind = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/find.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionFind.setIcon(icon)
        self.actionFind.setObjectName("actionFind")
        self.actionFind_Again = QtGui.QAction(MainWindow)
        self.actionFind_Again.setObjectName("actionFind_Again")
        self.actionShow_Only_Unread_Feeds = QtGui.QAction(MainWindow)
        self.actionShow_Only_Unread_Feeds.setCheckable(True)
        self.actionShow_Only_Unread_Feeds.setObjectName("actionShow_Only_Unread_Feeds")
        self.actionOpen_Homepage = QtGui.QAction(MainWindow)
        self.actionOpen_Homepage.setObjectName("actionOpen_Homepage")
        self.actionDelete_Feed = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/editdelete.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionDelete_Feed.setIcon(icon)
        self.actionDelete_Feed.setObjectName("actionDelete_Feed")
        self.actionAdd_Feed = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/filenew.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionAdd_Feed.setIcon(icon)
        self.actionAdd_Feed.setObjectName("actionAdd_Feed")
        self.actionNew_Folder = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/folder_new.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionNew_Folder.setIcon(icon)
        self.actionNew_Folder.setObjectName("actionNew_Folder")
        self.actionEdit_Feed = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/edit.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionEdit_Feed.setIcon(icon)
        self.actionEdit_Feed.setObjectName("actionEdit_Feed")
        self.actionMark_as_Read = QtGui.QAction(MainWindow)
        self.actionMark_as_Read.setObjectName("actionMark_as_Read")
        self.actionMark_as_Unread = QtGui.QAction(MainWindow)
        self.actionMark_as_Unread.setObjectName("actionMark_as_Unread")
        self.actionMark_as_Important = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/flag.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionMark_as_Important.setIcon(icon)
        self.actionMark_as_Important.setObjectName("actionMark_as_Important")
        self.actionDelete_Article = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/editdelete.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionDelete_Article.setIcon(icon)
        self.actionDelete_Article.setObjectName("actionDelete_Article")
        self.actionOpen_in_Browser = QtGui.QAction(MainWindow)
        self.actionOpen_in_Browser.setObjectName("actionOpen_in_Browser")
        self.actionRemove_Important_Mark = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/flag.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionRemove_Important_Mark.setIcon(icon)
        self.actionRemove_Important_Mark.setObjectName("actionRemove_Important_Mark")
        self.actionExpire_Feed = QtGui.QAction(MainWindow)
        self.actionExpire_Feed.setObjectName("actionExpire_Feed")
        self.toolBar.addAction(self.actionFetch_Feed)
        self.toolBar.addAction(self.actionFetch_All_Feeds)
        self.toolBar.addAction(self.actionAbort_Fetches)
        self.toolBar.addAction(self.actionMark_Feed_as_Read)
        self.menuFeed.addSeparator()
        self.menuFeed.addAction(self.actionAdd_Feed)
        self.menuFeed.addAction(self.actionNew_Folder)
        self.menuFeed.addSeparator()
        self.menuFeed.addAction(self.actionMark_Feed_as_Read)
        self.menuFeed.addSeparator()
        self.menuFeed.addAction(self.actionFetch_Feed)
        self.menuFeed.addAction(self.actionFetch_All_Feeds)
        self.menuFeed.addAction(self.actionAbort_Fetches)
        self.menuFeed.addSeparator()
        self.menuFeed.addAction(self.actionEdit_Feed)
        self.menuFeed.addAction(self.actionExpire_Feed)
        self.menuFeed.addAction(self.actionDelete_Feed)
        self.menu_File.addAction(self.actionImport_Feeds)
        self.menu_File.addAction(self.actionExport_Feeds)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.actionQuit)
        self.menu_Go.addSeparator()
        self.menu_Go.addAction(self.actionPrevious_Article)
        self.menu_Go.addAction(self.actionPrevious_Unread_Article)
        self.menu_Go.addAction(self.actionNext_Article)
        self.menu_Go.addAction(self.actionNext_Unread_Article)
        self.menu_Go.addSeparator()
        self.menu_Go.addAction(self.actionPrevious_Feed)
        self.menu_Go.addAction(self.actionPrevious_Unread_Feed)
        self.menu_Go.addAction(self.actionNext_Feed)
        self.menu_Go.addAction(self.actionNext_Unread_Feed)
        self.menuHelp.addAction(self.actionAbout_uRSSus)
        self.menu_View.addAction(self.actionStatus_Bar)
        self.menu_View.addSeparator()
        self.menu_View.addAction(self.actionShow_Only_Unread_Feeds)
        self.menu_View.addSeparator()
        self.menu_View.addAction(self.actionIncrease_Font_Sizes)
        self.menu_View.addAction(self.actionDecrease_Font_Sizes)
        self.menu_Edit.addAction(self.actionFind)
        self.menu_Edit.addAction(self.actionFind_Again)
        self.menuArticle.addAction(self.actionOpen_in_Browser)
        self.menuArticle.addSeparator()
        self.menuArticle.addAction(self.actionMark_as_Important)
        self.menuArticle.addAction(self.actionRemove_Important_Mark)
        self.menuArticle.addAction(self.actionMark_as_Read)
        self.menuArticle.addAction(self.actionMark_as_Unread)
        self.menuArticle.addAction(self.actionDelete_Article)
        self.menuBar.addAction(self.menu_File.menuAction())
        self.menuBar.addAction(self.menu_Edit.menuAction())
        self.menuBar.addAction(self.menu_View.menuAction())
        self.menuBar.addAction(self.menu_Go.menuAction())
        self.menuBar.addAction(self.menuFeed.menuAction())
        self.menuBar.addAction(self.menuArticle.menuAction())
        self.menuBar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "uRSSus", None, QtGui.QApplication.UnicodeUTF8))
        self.toolBar.setWindowTitle(QtGui.QApplication.translate("MainWindow", "toolBar", None, QtGui.QApplication.UnicodeUTF8))
        self.menuFeed.setTitle(QtGui.QApplication.translate("MainWindow", "Fee&d", None, QtGui.QApplication.UnicodeUTF8))
        self.menu_File.setTitle(QtGui.QApplication.translate("MainWindow", "&File", None, QtGui.QApplication.UnicodeUTF8))
        self.menu_Go.setTitle(QtGui.QApplication.translate("MainWindow", "&Go", None, QtGui.QApplication.UnicodeUTF8))
        self.menuHelp.setTitle(QtGui.QApplication.translate("MainWindow", "&Help", None, QtGui.QApplication.UnicodeUTF8))
        self.menu_View.setTitle(QtGui.QApplication.translate("MainWindow", "&View", None, QtGui.QApplication.UnicodeUTF8))
        self.menu_Edit.setTitle(QtGui.QApplication.translate("MainWindow", "&Edit", None, QtGui.QApplication.UnicodeUTF8))
        self.menuArticle.setTitle(QtGui.QApplication.translate("MainWindow", "&Article", None, QtGui.QApplication.UnicodeUTF8))
        self.filterBar.setWindowTitle(QtGui.QApplication.translate("MainWindow", "toolBar_2", None, QtGui.QApplication.UnicodeUTF8))
        self.actionFetch_Feed.setText(QtGui.QApplication.translate("MainWindow", "Fetch Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.actionFetch_Feed.setShortcut(QtGui.QApplication.translate("MainWindow", "F5", None, QtGui.QApplication.UnicodeUTF8))
        self.actionFetch_All_Feeds.setText(QtGui.QApplication.translate("MainWindow", "Fetch All Feeds", None, QtGui.QApplication.UnicodeUTF8))
        self.actionFetch_All_Feeds.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+L", None, QtGui.QApplication.UnicodeUTF8))
        self.actionAbort_Fetches.setText(QtGui.QApplication.translate("MainWindow", "Abort Fetches", None, QtGui.QApplication.UnicodeUTF8))
        self.actionAbort_Fetches.setShortcut(QtGui.QApplication.translate("MainWindow", "Esc", None, QtGui.QApplication.UnicodeUTF8))
        self.actionMark_Feed_as_Read.setText(QtGui.QApplication.translate("MainWindow", "Mark Feed as Read", None, QtGui.QApplication.UnicodeUTF8))
        self.actionMark_Feed_as_Read.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+R", None, QtGui.QApplication.UnicodeUTF8))
        self.actionImport_Feeds.setText(QtGui.QApplication.translate("MainWindow", "&Import Feeds...", None, QtGui.QApplication.UnicodeUTF8))
        self.actionExport_Feeds.setText(QtGui.QApplication.translate("MainWindow", "&Export Feeds...", None, QtGui.QApplication.UnicodeUTF8))
        self.actionQuit.setText(QtGui.QApplication.translate("MainWindow", "&Quit", None, QtGui.QApplication.UnicodeUTF8))
        self.actionQuit.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+Q", None, QtGui.QApplication.UnicodeUTF8))
        self.actionNext_Article.setText(QtGui.QApplication.translate("MainWindow", "&Next Article", None, QtGui.QApplication.UnicodeUTF8))
        self.actionNext_Article.setShortcut(QtGui.QApplication.translate("MainWindow", "Right", None, QtGui.QApplication.UnicodeUTF8))
        self.actionNext_Unread_Article.setText(QtGui.QApplication.translate("MainWindow", "Ne&xt Unread Article", None, QtGui.QApplication.UnicodeUTF8))
        self.actionNext_Unread_Article.setShortcut(QtGui.QApplication.translate("MainWindow", "+", None, QtGui.QApplication.UnicodeUTF8))
        self.actionNext_Feed.setText(QtGui.QApplication.translate("MainWindow", "Next &Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.actionNext_Feed.setShortcut(QtGui.QApplication.translate("MainWindow", "N", None, QtGui.QApplication.UnicodeUTF8))
        self.actionNext_Unread_Feed.setText(QtGui.QApplication.translate("MainWindow", "N&ext Unread Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.actionNext_Unread_Feed.setShortcut(QtGui.QApplication.translate("MainWindow", "Alt++", None, QtGui.QApplication.UnicodeUTF8))
        self.actionAbout_uRSSus.setText(QtGui.QApplication.translate("MainWindow", "&About uRSSus...", None, QtGui.QApplication.UnicodeUTF8))
        self.actionIncrease_Font_Sizes.setText(QtGui.QApplication.translate("MainWindow", "Increase Font Sizes", None, QtGui.QApplication.UnicodeUTF8))
        self.actionIncrease_Font_Sizes.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl++", None, QtGui.QApplication.UnicodeUTF8))
        self.actionDecrease_Font_Sizes.setText(QtGui.QApplication.translate("MainWindow", "Decrease Font Sizes", None, QtGui.QApplication.UnicodeUTF8))
        self.actionDecrease_Font_Sizes.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+-", None, QtGui.QApplication.UnicodeUTF8))
        self.actionStatus_Bar.setText(QtGui.QApplication.translate("MainWindow", "Status Bar", None, QtGui.QApplication.UnicodeUTF8))
        self.actionPrevious_Feed.setText(QtGui.QApplication.translate("MainWindow", "P&revious Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.actionPrevious_Feed.setShortcut(QtGui.QApplication.translate("MainWindow", "P", None, QtGui.QApplication.UnicodeUTF8))
        self.actionPrevious_Unread_Feed.setText(QtGui.QApplication.translate("MainWindow", "Prev&ious Unread Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.actionPrevious_Unread_Feed.setShortcut(QtGui.QApplication.translate("MainWindow", "Alt+-", None, QtGui.QApplication.UnicodeUTF8))
        self.actionPrevious_Article.setText(QtGui.QApplication.translate("MainWindow", "&Previous Article", None, QtGui.QApplication.UnicodeUTF8))
        self.actionPrevious_Article.setShortcut(QtGui.QApplication.translate("MainWindow", "Left", None, QtGui.QApplication.UnicodeUTF8))
        self.actionPrevious_Unread_Article.setText(QtGui.QApplication.translate("MainWindow", "Pre&vious Unread Article", None, QtGui.QApplication.UnicodeUTF8))
        self.actionPrevious_Unread_Article.setShortcut(QtGui.QApplication.translate("MainWindow", "-", None, QtGui.QApplication.UnicodeUTF8))
        self.actionFind.setText(QtGui.QApplication.translate("MainWindow", "&Find", None, QtGui.QApplication.UnicodeUTF8))
        self.actionFind.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+F", None, QtGui.QApplication.UnicodeUTF8))
        self.actionFind_Again.setText(QtGui.QApplication.translate("MainWindow", "Find Again", None, QtGui.QApplication.UnicodeUTF8))
        self.actionFind_Again.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+G", None, QtGui.QApplication.UnicodeUTF8))
        self.actionShow_Only_Unread_Feeds.setText(QtGui.QApplication.translate("MainWindow", "Show Only Unread Feeds", None, QtGui.QApplication.UnicodeUTF8))
        self.actionOpen_Homepage.setText(QtGui.QApplication.translate("MainWindow", "Open Homepage", None, QtGui.QApplication.UnicodeUTF8))
        self.actionOpen_Homepage.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+H", None, QtGui.QApplication.UnicodeUTF8))
        self.actionDelete_Feed.setText(QtGui.QApplication.translate("MainWindow", "&Delete Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.actionDelete_Feed.setShortcut(QtGui.QApplication.translate("MainWindow", "Alt+Del", None, QtGui.QApplication.UnicodeUTF8))
        self.actionAdd_Feed.setText(QtGui.QApplication.translate("MainWindow", "Add Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.actionAdd_Feed.setShortcut(QtGui.QApplication.translate("MainWindow", "Ins", None, QtGui.QApplication.UnicodeUTF8))
        self.actionNew_Folder.setText(QtGui.QApplication.translate("MainWindow", "New Folder", None, QtGui.QApplication.UnicodeUTF8))
        self.actionNew_Folder.setShortcut(QtGui.QApplication.translate("MainWindow", "Shift+Ins", None, QtGui.QApplication.UnicodeUTF8))
        self.actionEdit_Feed.setText(QtGui.QApplication.translate("MainWindow", "&Edit Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.actionEdit_Feed.setShortcut(QtGui.QApplication.translate("MainWindow", "F2", None, QtGui.QApplication.UnicodeUTF8))
        self.actionMark_as_Read.setText(QtGui.QApplication.translate("MainWindow", "Mark as Read", None, QtGui.QApplication.UnicodeUTF8))
        self.actionMark_as_Read.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+E", None, QtGui.QApplication.UnicodeUTF8))
        self.actionMark_as_Unread.setText(QtGui.QApplication.translate("MainWindow", "Mark as Unread", None, QtGui.QApplication.UnicodeUTF8))
        self.actionMark_as_Unread.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+U", None, QtGui.QApplication.UnicodeUTF8))
        self.actionMark_as_Important.setText(QtGui.QApplication.translate("MainWindow", "Mark as Important", None, QtGui.QApplication.UnicodeUTF8))
        self.actionMark_as_Important.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+I", None, QtGui.QApplication.UnicodeUTF8))
        self.actionDelete_Article.setText(QtGui.QApplication.translate("MainWindow", "Delete Article", None, QtGui.QApplication.UnicodeUTF8))
        self.actionDelete_Article.setShortcut(QtGui.QApplication.translate("MainWindow", "Del", None, QtGui.QApplication.UnicodeUTF8))
        self.actionOpen_in_Browser.setText(QtGui.QApplication.translate("MainWindow", "Open in Browser", None, QtGui.QApplication.UnicodeUTF8))
        self.actionOpen_in_Browser.setShortcut(QtGui.QApplication.translate("MainWindow", "Shift+Return", None, QtGui.QApplication.UnicodeUTF8))
        self.actionRemove_Important_Mark.setText(QtGui.QApplication.translate("MainWindow", "Remove Important Mark", None, QtGui.QApplication.UnicodeUTF8))
        self.actionRemove_Important_Mark.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+Shift+I", None, QtGui.QApplication.UnicodeUTF8))
        self.actionExpire_Feed.setText(QtGui.QApplication.translate("MainWindow", "Expire Feed", None, QtGui.QApplication.UnicodeUTF8))

from PyQt4 import QtWebKit
import icons_rc

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    MainWindow = QtGui.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

