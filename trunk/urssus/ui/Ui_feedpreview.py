# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'urssus/ui/feedpreview.ui'
#
# Created: Sun Dec 13 21:12:50 2009
#      by: PyQt4 UI code generator 4.6.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(617, 408)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.ExpandingFieldsGrow)
        self.formLayout.setObjectName("formLayout")
        self.label_2 = QtGui.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_2)
        self.feedType = QtGui.QComboBox(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.feedType.sizePolicy().hasHeightForWidth())
        self.feedType.setSizePolicy(sizePolicy)
        self.feedType.setObjectName("feedType")
        self.feedType.addItem("")
        self.feedType.addItem("")
        self.feedType.addItem("")
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.feedType)
        self.label_3 = QtGui.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_3)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setSpacing(-1)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.data = QtGui.QLineEdit(Dialog)
        self.data.setObjectName("data")
        self.horizontalLayout_2.addWidget(self.data)
        self.go = QtGui.QToolButton(Dialog)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/1rightarrow.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.go.setIcon(icon)
        self.go.setObjectName("go")
        self.horizontalLayout_2.addWidget(self.go)
        self.formLayout.setLayout(1, QtGui.QFormLayout.FieldRole, self.horizontalLayout_2)
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName("label")
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label)
        self.feeds = QtGui.QComboBox(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.feeds.sizePolicy().hasHeightForWidth())
        self.feeds.setSizePolicy(sizePolicy)
        self.feeds.setObjectName("feeds")
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.feeds)
        self.verticalLayout.addLayout(self.formLayout)
        self.preview = QtWebKit.QWebView(Dialog)
        self.preview.setUrl(QtCore.QUrl("about:blank"))
        self.preview.setObjectName("preview")
        self.verticalLayout.addWidget(self.preview)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.addFeed = QtGui.QPushButton(Dialog)
        self.addFeed.setObjectName("addFeed")
        self.horizontalLayout.addWidget(self.addFeed)
        self.pushButton_2 = QtGui.QPushButton(Dialog)
        self.pushButton_2.setObjectName("pushButton_2")
        self.horizontalLayout.addWidget(self.pushButton_2)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.label_2.setBuddy(self.feedType)
        self.label_3.setBuddy(self.data)
        self.label.setBuddy(self.feeds)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.pushButton_2, QtCore.SIGNAL("clicked()"), Dialog.accept)
        QtCore.QObject.connect(self.data, QtCore.SIGNAL("editingFinished()"), self.go.animateClick)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "uRSSus - Add Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Dialog", "Feed &Type:", None, QtGui.QApplication.UnicodeUTF8))
        self.feedType.setItemText(0, QtGui.QApplication.translate("Dialog", "Regular Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.feedType.setItemText(1, QtGui.QApplication.translate("Dialog", "Google News Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.feedType.setItemText(2, QtGui.QApplication.translate("Dialog", "Bloglines Search", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Dialog", "URL:", None, QtGui.QApplication.UnicodeUTF8))
        self.go.setText(QtGui.QApplication.translate("Dialog", "...", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Available Feeds:", None, QtGui.QApplication.UnicodeUTF8))
        self.addFeed.setText(QtGui.QApplication.translate("Dialog", "&Add", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButton_2.setText(QtGui.QApplication.translate("Dialog", "&Close", None, QtGui.QApplication.UnicodeUTF8))

from PyQt4 import QtWebKit
import icons_rc

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    Dialog = QtGui.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())

