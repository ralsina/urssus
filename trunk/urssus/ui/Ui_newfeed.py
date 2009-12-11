# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'urssus/ui/newfeed.ui'
#
# Created: Fri Feb 27 23:57:11 2009
#      by: PyQt4 UI code generator 4.4.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(384, 165)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/urssus.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        Dialog.setWindowIcon(icon)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_2 = QtGui.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.feedType = QtGui.QComboBox(Dialog)
        self.feedType.setObjectName("feedType")
        self.feedType.addItem(QtCore.QString())
        self.feedType.addItem(QtCore.QString())
        self.feedType.addItem(QtCore.QString())
        self.horizontalLayout.addWidget(self.feedType)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.label = QtGui.QLabel(Dialog)
        self.label.setTextFormat(QtCore.Qt.RichText)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        spacerItem = QtGui.QSpacerItem(20, 20, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.data = QtGui.QLineEdit(Dialog)
        self.data.setObjectName("data")
        self.verticalLayout.addWidget(self.data)
        spacerItem1 = QtGui.QSpacerItem(20, 22, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        self.buttonBox = QtGui.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)
        self.label_2.setBuddy(self.feedType)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), Dialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)
        Dialog.setTabOrder(self.data, self.feedType)
        Dialog.setTabOrder(self.feedType, self.buttonBox)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "New Feed - uRSSus", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Dialog", "Feed &Type:", None, QtGui.QApplication.UnicodeUTF8))
        self.feedType.setItemText(0, QtGui.QApplication.translate("Dialog", "Regular Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.feedType.setItemText(1, QtGui.QApplication.translate("Dialog", "Google News Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.feedType.setItemText(2, QtGui.QApplication.translate("Dialog", "Bloglines Search", None, QtGui.QApplication.UnicodeUTF8))

import icons_rc
