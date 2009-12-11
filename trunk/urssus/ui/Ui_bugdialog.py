# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'urssus/ui/bugdialog.ui'
#
# Created: Fri Feb 27 23:57:11 2009
#      by: PyQt4 UI code generator 4.4.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(414, 369)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.toolBox = QtGui.QToolBox(Dialog)
        self.toolBox.setObjectName("toolBox")
        self.page = QtGui.QWidget()
        self.page.setGeometry(QtCore.QRect(0, 0, 396, 255))
        self.page.setObjectName("page")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.page)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label = QtGui.QLabel(self.page)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        spacerItem = QtGui.QSpacerItem(20, 68, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
        self.toolBox.addItem(self.page, "")
        self.page_2 = QtGui.QWidget()
        self.page_2.setGeometry(QtCore.QRect(0, 0, 396, 255))
        self.page_2.setObjectName("page_2")
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.page_2)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.report = QtGui.QTextBrowser(self.page_2)
        self.report.setObjectName("report")
        self.verticalLayout_3.addWidget(self.report)
        self.toolBox.addItem(self.page_2, "")
        self.verticalLayout.addWidget(self.toolBox)
        self.buttonBox = QtGui.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(Dialog)
        self.toolBox.setCurrentIndex(1)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), Dialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Error report - uRSSus", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Because uRSSus is a very young application, sometimes it does strange things. One just happened!\n"
"\n"
"If you agree, uRSSus would like to call his dad and tell him what happened.\n"
"\n"
"Click on \"Error report\" to see a copy of the message that would be sent.\n"
"\n"
"No personal data will be transferred in any way.", None, QtGui.QApplication.UnicodeUTF8))
        self.toolBox.setItemText(self.toolBox.indexOf(self.page), QtGui.QApplication.translate("Dialog", "Information", None, QtGui.QApplication.UnicodeUTF8))
        self.toolBox.setItemText(self.toolBox.indexOf(self.page_2), QtGui.QApplication.translate("Dialog", "Error report", None, QtGui.QApplication.UnicodeUTF8))

