# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'urssus/ui/twitterpost.ui'
#
# Created: Tue Mar  3 17:38:13 2009
#      by: PyQt4 UI code generator 4.4.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(400, 242)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/urssus.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        Dialog.setWindowIcon(icon)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_4 = QtGui.QLabel(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(32)
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)
        self.label_4.setMaximumSize(QtCore.QSize(32, 32))
        self.label_4.setPixmap(QtGui.QPixmap(":/twitter.svg"))
        self.label_4.setScaledContents(True)
        self.label_4.setObjectName("label_4")
        self.horizontalLayout_2.addWidget(self.label_4)
        self.username = QtGui.QLabel(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.username.sizePolicy().hasHeightForWidth())
        self.username.setSizePolicy(sizePolicy)
        self.username.setObjectName("username")
        self.horizontalLayout_2.addWidget(self.username)
        self.changeAuth = QtGui.QPushButton(Dialog)
        self.changeAuth.setObjectName("changeAuth")
        self.horizontalLayout_2.addWidget(self.changeAuth)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.message = QtGui.QTextEdit(Dialog)
        self.message.setAcceptRichText(False)
        self.message.setObjectName("message")
        self.verticalLayout.addWidget(self.message)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.counter = QtGui.QLabel(Dialog)
        self.counter.setObjectName("counter")
        self.horizontalLayout.addWidget(self.counter)
        self.label_3 = QtGui.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout.addWidget(self.label_3)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem1)
        self.ok = QtGui.QPushButton(Dialog)
        self.ok.setObjectName("ok")
        self.horizontalLayout_3.addWidget(self.ok)
        self.pushButton_2 = QtGui.QPushButton(Dialog)
        self.pushButton_2.setObjectName("pushButton_2")
        self.horizontalLayout_3.addWidget(self.pushButton_2)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.label.setBuddy(self.message)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.ok, QtCore.SIGNAL("clicked()"), Dialog.accept)
        QtCore.QObject.connect(self.pushButton_2, QtCore.SIGNAL("clicked()"), Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Twitter Post - uRSSus", None, QtGui.QApplication.UnicodeUTF8))
        self.username.setText(QtGui.QApplication.translate("Dialog", "Posting as: PPPPPP", None, QtGui.QApplication.UnicodeUTF8))
        self.changeAuth.setText(QtGui.QApplication.translate("Dialog", "Change", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "&Your Update:", None, QtGui.QApplication.UnicodeUTF8))
        self.message.setHtml(QtGui.QApplication.translate("Dialog", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Verdana\'; font-size:8pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.counter.setText(QtGui.QApplication.translate("Dialog", "140 ", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Dialog", "Characters left.", None, QtGui.QApplication.UnicodeUTF8))
        self.ok.setText(QtGui.QApplication.translate("Dialog", "&Ok", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButton_2.setText(QtGui.QApplication.translate("Dialog", "&Cancel", None, QtGui.QApplication.UnicodeUTF8))

import icons_rc
