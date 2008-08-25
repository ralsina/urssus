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

from PyQt4 import QtGui, QtCore
import processing

from ui.Ui_runprocess import Ui_Dialog as UI_ProcessDialog

class ProcessDialog(QtGui.QDialog):
  def __init__(self, parent, callable, args):
    QtGui.QDialog.__init__(self, parent)
    # Set up the UI from designer
    self.ui=UI_ProcessDialog()
    self.ui.setupUi(self)
    self.output=processing.Queue()
    self.callable=callable
    self.args=args+[self.output]
    self.timer=QtCore.QTimer(self)
    QtCore.QObject.connect(self.timer, QtCore.SIGNAL("timeout()"), self.showOutput)
    self.proc=None


  def exec_(self):
    self.show()
    self.start()
    return QtGui.QDialog.exec_(self)

  def start(self):
    self.proc=processing.Process(target=self.callable, args=self.args)
    self.proc.start()
    self.showOutput()
    
  def reject(self):
    if self.proc and self.proc.isAlive():
      self.proc.terminate()
    return QtGui.QDialog.reject(self)
    
  def showOutput(self):
    while not self.output.empty():
      [code, data]=self.output.get()
      if code==0: # Regular output
        self.ui.output.append(data+'<br>')
      elif code==1:
        self.ui.output.append('<b>'+data+'<b><br>')
      elif code==2: # Really bad
        QtGui.QMessageBox.critical(self, 'Error - uRSSus', data )
        self.reject()
      elif code==100: # The result data
        self.result=data
        self.accept()

    if self.proc.isAlive():
      self.timer.setInterval(500)
      self.timer.start()
