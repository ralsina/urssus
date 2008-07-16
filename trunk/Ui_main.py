# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/ralsina/Desktop/proyectos/urssus/main.ui'
#
# Created: Tue Jul 15 23:37:47 2008
#      by: PyQt4 UI code generator 4.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800,600)
        self.centralWidget = QtGui.QWidget(MainWindow)
        self.centralWidget.setGeometry(QtCore.QRect(0,46,800,554))
        self.centralWidget.setObjectName("centralWidget")
        self.horizontalLayout = QtGui.QHBoxLayout(self.centralWidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.splitter_2 = QtGui.QSplitter(self.centralWidget)
        self.splitter_2.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_2.setObjectName("splitter_2")
        self.feeds = QtGui.QTreeView(self.splitter_2)
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
        self.toolBar.setGeometry(QtCore.QRect(0,31,800,15))
        self.toolBar.setObjectName("toolBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea,self.toolBar)
        self.menuBar = QtGui.QMenuBar(MainWindow)
        self.menuBar.setGeometry(QtCore.QRect(0,0,800,31))
        self.menuBar.setObjectName("menuBar")
        MainWindow.setMenuBar(self.menuBar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "MainWindow", None, QtGui.QApplication.UnicodeUTF8))
        self.toolBar.setWindowTitle(QtGui.QApplication.translate("MainWindow", "toolBar", None, QtGui.QApplication.UnicodeUTF8))

from PyQt4 import QtWebKit

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    MainWindow = QtGui.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

