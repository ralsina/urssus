# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/ralsina/Desktop/proyectos/urssus/main.ui'
#
# Created: Wed Jul 16 22:08:46 2008
#      by: PyQt4 UI code generator 4.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800,600)
        self.centralWidget = QtGui.QWidget(MainWindow)
        self.centralWidget.setGeometry(QtCore.QRect(0,70,800,506))
        self.centralWidget.setObjectName("centralWidget")
        self.horizontalLayout = QtGui.QHBoxLayout(self.centralWidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.splitter_2 = QtGui.QSplitter(self.centralWidget)
        self.splitter_2.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_2.setObjectName("splitter_2")
        self.feeds = QtGui.QTreeView(self.splitter_2)
        self.feeds.setAlternatingRowColors(True)
        self.feeds.setAnimated(True)
        self.feeds.setHeaderHidden(True)
        self.feeds.setObjectName("feeds")
        self.splitter = QtGui.QSplitter(self.splitter_2)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setObjectName("splitter")
        self.posts = QtGui.QListView(self.splitter)
        self.posts.setObjectName("posts")
        self.view = QtWebKit.QWebView(self.splitter)
        self.view.setUrl(QtCore.QUrl("about:blank"))
        self.view.setObjectName("view")
        self.horizontalLayout.addWidget(self.splitter_2)
        MainWindow.setCentralWidget(self.centralWidget)
        self.toolBar = QtGui.QToolBar(MainWindow)
        self.toolBar.setGeometry(QtCore.QRect(0,31,800,39))
        self.toolBar.setObjectName("toolBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea,self.toolBar)
        self.menuBar = QtGui.QMenuBar(MainWindow)
        self.menuBar.setGeometry(QtCore.QRect(0,0,800,31))
        self.menuBar.setObjectName("menuBar")
        MainWindow.setMenuBar(self.menuBar)
        self.statusBar = QtGui.QStatusBar(MainWindow)
        self.statusBar.setGeometry(QtCore.QRect(0,576,800,24))
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)
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
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/stop.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionAbort_Fetches.setIcon(icon)
        self.actionAbort_Fetches.setObjectName("actionAbort_Fetches")
        self.actionMark_Feed_as_Read = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/apply.svg"),QtGui.QIcon.Normal,QtGui.QIcon.Off)
        self.actionMark_Feed_as_Read.setIcon(icon)
        self.actionMark_Feed_as_Read.setObjectName("actionMark_Feed_as_Read")
        self.toolBar.addAction(self.actionFetch_Feed)
        self.toolBar.addAction(self.actionFetch_All_Feeds)
        self.toolBar.addAction(self.actionAbort_Fetches)
        self.toolBar.addAction(self.actionMark_Feed_as_Read)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "uRSSus", None, QtGui.QApplication.UnicodeUTF8))
        self.toolBar.setWindowTitle(QtGui.QApplication.translate("MainWindow", "toolBar", None, QtGui.QApplication.UnicodeUTF8))
        self.actionFetch_Feed.setText(QtGui.QApplication.translate("MainWindow", "Fetch Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.actionFetch_All_Feeds.setText(QtGui.QApplication.translate("MainWindow", "Fetch All Feeds", None, QtGui.QApplication.UnicodeUTF8))
        self.actionAbort_Fetches.setText(QtGui.QApplication.translate("MainWindow", "Abort Fetches", None, QtGui.QApplication.UnicodeUTF8))
        self.actionMark_Feed_as_Read.setText(QtGui.QApplication.translate("MainWindow", "Mark Feed as Read", None, QtGui.QApplication.UnicodeUTF8))

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

