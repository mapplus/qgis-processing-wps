# -*- coding: utf-8 -*-
"""
/***************************************************************************
    CreateMDADatasetDialog.py
    ---------------------
    Date                 : January 2014
    Copyright            : (C) 2014 by Minpa Lee
    Email                : mapplus at gmail dot com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Minpa Lee'
__date__ = 'January 2014'
__copyright__ = '(C) 2014, Minpa Lee'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os, os.path, datetime

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtCore, QtGui, uic
from PyQt4.QtXml import *

from qgis.core import *
from qgis.gui import *
from qgis.utils import iface

import processing
from processing.core.ProcessingLog import ProcessingLog
from processing.tools.system import getTempFilenameInTempFolder
from processing.algs.ogcwps.WPSUtils import WPSUtils
from processing.algs.ogcwps.wps import WebProcessingService, Process, Input, Output

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'CreateMDADataset_dialog_base.ui'))


class CreateMDADatasetDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(CreateMDADatasetDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        QObject.connect(self.btnAdd, SIGNAL("clicked ()"), self.AddList)
        QObject.connect(self.btnDel, SIGNAL("clicked ()"), self.RemoveList)
        QObject.connect(self.btnOk, SIGNAL("clicked ()"), self.CreateMDADataset)

        #시간범위_cboSYear,cboEyear combobox setting
        now = datetime.datetime.now()
        for year in range(now.year, 1980, -1):
            self.cboSyear.addItem(str(year))
            self.cboEyear.addItem(str(year))
        
        self.cboSyear.setCurrentIndex(self.cboSyear.findText(str(2005)))
        self.cboEyear.setCurrentIndex(self.cboEyear.findText(str(2010)))
        
        #공간범위_cboLevel combobox setting
        self.cboLevel.addItem(u"시군구 경계")
        self.cboLevel.addItem(u"시도 경계")
        self.GetFileList()
        self.GetSidoFileList()

    def GetFileList(self):
        listFile = os.path.join(os.path.dirname(__file__),'index_metadata', 'index.xml')
        if os.path.exists(listFile):
            self.AddFileList(listFile)
        else:
            QMessageBox.information(self, "Information", u"Check File!")

    def AddFileList(self, listFile):
        tblistWiget = self.tbItem
        tbselListWiget = self.tbSelItem
        document = QDomDocument()
        f = QFile(listFile)
        if f.open(QtCore.QIODevice.ReadOnly):
            if document.setContent(f):
                f.close()
        
        elements = document.documentElement()
        node = elements.firstChild()
    
        #xml columns 생성
        headerNames = [u'지표이름', u'공간단위', u'시간범위', u'지표유형', u'지표코드', u'코드']
        tblistWiget.setColumnCount(len(headerNames))
        tblistWiget.setHorizontalHeaderLabels(headerNames)

        headerNames = [u'지표이름', u'지표코드']
        tbselListWiget.setColumnCount(len(headerNames))
        tbselListWiget.setHorizontalHeaderLabels(headerNames)
            
        #xml Rows 추가
        rowCnt = 0
        while node.isNull() is False:
            sub_node = node.toElement().firstChild()
            tblistWiget.setRowCount(rowCnt + 1)
            colCnt = 0
            column_values = []
            while sub_node.isNull() is False:
                sub_prop = sub_node.toElement()
                tblistWiget.setItem(rowCnt, colCnt, QTableWidgetItem(sub_prop.text()))
                column_values.append(sub_prop.text())
                colCnt += 1
                sub_node = sub_node.nextSibling()

            # XML에 지표의 시간범위가 없는 경우가 있는데 제외
            if len(column_values) != 6:
                node = node.nextSibling()
                continue

            tblistWiget.setItem(rowCnt, 0, QTableWidgetItem(column_values[0])) # 지표이름
            tblistWiget.setItem(rowCnt, 1, QTableWidgetItem(column_values[4])) # 공간단위
            tblistWiget.setItem(rowCnt, 2, QTableWidgetItem(column_values[5])) # 시간범위
            tblistWiget.setItem(rowCnt, 3, QTableWidgetItem(column_values[3])) # 지표유형
            tblistWiget.setItem(rowCnt, 4, QTableWidgetItem(column_values[1])) # 지표코드
            tblistWiget.setItem(rowCnt, 5, QTableWidgetItem(column_values[2])) # 코드

            rowCnt += 1
            node = node.nextSibling()
      
        tblistWiget.show()
        tbselListWiget.show()
        tblistWiget.resizeColumnsToContents()
    
    def AddList(self):
        tblistWidget = self.tbItem
        tbselListWidget = self.tbSelItem
    
        # [u'지표이름', u'지표코드']
        rowCnt = tbselListWidget.rowCount()
        selectedList = tblistWidget.selectionModel().selectedRows()
        for index in selectedList:
            row = index.row()
            tbselListWidget.setRowCount(rowCnt + 1)

            # 지표이름
            cellValue = tblistWidget.item(row, 0).text()
            tbselListWidget.setItem(rowCnt, 0, QTableWidgetItem(cellValue))
            
            # 지표코드
            cellValue = tblistWidget.item(row, 4).text()
            tbselListWidget.setItem(rowCnt, 1, QTableWidgetItem(cellValue))

            rowCnt += 1
        tbselListWidget.resizeColumnsToContents()
        
    def RemoveList(self):
        tbselListWidget = self.tbSelItem
        selectedList = tbselListWidget.selectionModel().selectedRows()
        for index in selectedList:
            row = index.row()
            tbselListWidget.removeRow(row)

    def GetSidoFileList(self):
        listSidFile = os.path.join(os.path.dirname(__file__),'index_metadata', 'region.xml')
        if os.path.exists(listSidFile):
            self.AddSidFileList(listSidFile)
        else:
            QMessageBox.information(self, "Information", u"Check File!")
        
    def AddSidFileList(self, listSidFile):
        tbSidListWidget = self.tbSid

        document = QDomDocument()
        f = QFile(listSidFile)
        if f.open(QtCore.QIODevice.ReadOnly):
            if document.setContent(f):
                f.close()
        
        elements = document.documentElement()
        node = elements.firstChild()
    
        #xml columns 생성
        headerNames = [u'시도명', u'시도 코드']
        tbSidListWidget.setColumnCount(len(headerNames))
        tbSidListWidget.setHorizontalHeaderLabels(headerNames)
            
        #xml Rows 추가
        rowCnt = 0
        while node.isNull() is False:
            property = node.toElement()
            sub_node = property.firstChild()
            tbSidListWidget.setRowCount(rowCnt + 1)
            colCnt = 0
            while sub_node.isNull() is False:
                sub_prop = sub_node.toElement()
                tbSidListWidget.setItem(rowCnt, colCnt, QTableWidgetItem(sub_prop.text()))
                #CheckBox 넣기
                tbSidListWidget.item(rowCnt, 0).setCheckState(QtCore.Qt.Unchecked)
                #User Action
                tbSidListWidget.item(rowCnt, 0).setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable)
                colCnt += 1
                sub_node = sub_node.nextSibling()
            rowCnt += 1
            node = node.nextSibling()
      
        tbSidListWidget.show()

    def CreateMDADataset(self):
        customArea = u"" #시도 및 시군구 코드 목록
        mapLevel = u"" #시도, 시군구, 읍면동
        period = u"" #1985~2010
        factorList = u"" #지표 코드
    
        #선택지표 Table
        tbJipyoCtl = self.tbSelItem
        #SIDO Table
        tbSidCtl = self.tbSid
        #시작 시간범위
        tbSyearCtl = self.cboSyear
        #종료 시간범위
        tbEyearCtl = self.cboEyear
        #공간범위
        cboLevelCtl = self.cboLevel
    
        #선택지표 index_code 추출
        idx_code_num = 1 #index_code column number       
        rowCnt = tbJipyoCtl.rowCount()
        for row in range(rowCnt):
            if factorList == u"":
                factorList += tbJipyoCtl.item(row, idx_code_num).text()
            else:
                factorList += u"," + tbJipyoCtl.item(row, idx_code_num).text()

        if len(factorList) == 0:
            QMessageBox.information(iface.mainWindow(), 'Information', 
                u'지표 목록은 반드시 하나 이상 선택해야 합니다.')
            return
    
        #mapLevel 추출
        if cboLevelCtl.currentText() == u"시도 경계":
            mapLevel = u"SID"
        else:
            mapLevel = u"SGG"

        if len(mapLevel) == 0:
            QMessageBox.information(iface.mainWindow(), 'Information', 
                u'시도 또는 시군구의 공간 범위는 반드시 선택해야 합니다.')
            return
    
        #Year 추출
        sYear = tbSyearCtl.currentText()
        eYear = tbEyearCtl.currentText()
        period = sYear + u"~" + eYear

        if (int(sYear) - int(eYear)) > 0:
            QMessageBox.information(iface.mainWindow(), 'Information', 
                u'시작 년도가 종료 년도보다 작아야 합니다.')
            return

        #customArea 추출
        sid_code_num = 1
        sidRowCnt = tbSidCtl.rowCount()
        for row in range(sidRowCnt):
            if tbSidCtl.item(row, 0).checkState() == QtCore.Qt.Checked:
                if customArea == u"":
                    customArea += tbSidCtl.item(row, sid_code_num).text()
                else:
                    customArea += u"," + tbSidCtl.item(row, sid_code_num).text()

        if len(customArea) == 0:
            QMessageBox.information(iface.mainWindow(), 'Information', 
                u'생성 범위는 반드시 하나 이상 선택해야 합니다.')
            return

        #Execute WPS Process
        data_inputs = []
        data_inputs.append(('customArea', customArea.encode('utf8')))
        data_inputs.append(('mapLevel', mapLevel.encode('utf8')))
        data_inputs.append(('period', period.encode('utf8')))
        data_inputs.append(('factorList', factorList.encode('utf8')))

        process_outputs = []
        process_outputs.append(('result', u'text/xml; subtype=gml/3.1.1'))
         
        try:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

            # run process
            wps = WebProcessingService("http://geeps.krihs.re.kr/gxt/wps", verbose=False, skip_caps=True)
            execution = wps.execute('kopss:KM_CreateMDADataset', data_inputs, process_outputs)

            while execution.isComplete()==False:
                execution.checkStatus(sleepSecs=3)
                print 'Execution status: %s' % execution.status
            
            if execution.isSucceded():
                gml_path = getTempFilenameInTempFolder('result.gml')
                execution.getOutput(filepath=gml_path)

                layer_name = u"MDA_" + mapLevel + u"_" + sYear + u"_" + eYear
                wfs_layer = QgsVectorLayer(gml_path, layer_name, "ogr")
                QgsMapLayerRegistry.instance().addMapLayer(wfs_layer)
                
                self.close()
                QMessageBox.information(iface.mainWindow(), 'Information', 
                    layer_name + u' 레이어 이름으로 추가되었습니다.')
            else:
                QMessageBox.information(iface.mainWindow(), 'Information', 
                    u'데이터 추출에 실패했습니다. 네트워크 상태를 확인하거나 다시 시도해 보십시오.')
        except Exception, e:
            raise e
        finally:
            QApplication.restoreOverrideCursor()
            

