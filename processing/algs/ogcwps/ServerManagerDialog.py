# -*- coding: utf-8 -*-
"""
/***************************************************************************
    ServerManagerDialog.py
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
import shutil, ConfigParser

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
from processing.algs.ogcwps.WpsServerInfo import WpsServerInfo
from processing.algs.ogcwps.WPSUtils import WPSUtils
from processing.algs.ogcwps.wps import WebProcessingService, Process, Input, Output

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ServerManager_dialog_base.ui'))


class ServerManagerDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, provider, parent=None):
        """Constructor."""
        super(ServerManagerDialog, self).__init__(parent)
        
        self.setupUi(self)
        self.provider = provider
        self.server_dir = os.path.dirname(__file__) + "/wps_server/"
        self.servers = []
        
        QObject.connect(self.btnAdd, SIGNAL("clicked ()"), self.addServer)
        #QObject.connect(self.btnModify, SIGNAL("clicked ()"), self.modifyServer)
        QObject.connect(self.btnDelete, SIGNAL("clicked ()"), self.removeServer)
        
        QObject.connect(self.btnOk, SIGNAL("clicked ()"), self.apply)
        QObject.connect(self.btnCancel, SIGNAL("clicked ()"), self.cancel)
        
        self.loadServer()
    
    def loadServer(self):
        # table
        tableWidget = self.tblServer
        
        # create header
        headerNames = [u'이름', u'URL', u'버전', u'WPS 유형']
        tableWidget.setColumnCount(len(headerNames))
        tableWidget.setHorizontalHeaderLabels(headerNames)
        
        # load server
        Config = ConfigParser.ConfigParser()
        for serverName in os.listdir(self.server_dir):
            path = os.path.join(self.server_dir, serverName)
            if os.path.isfile(path):
                continue
                
            config_file = self.server_dir + serverName + ".ini"
            if not os.path.isfile(config_file):
                continue

            Config.read(config_file)
            serverName = Config.get('WPS', 'Name')
            serverURL = Config.get('WPS', 'URL')
            version = Config.get('WPS', 'Version')
            serverType = Config.get('WPS', 'ServerType')
            serverInfo = WpsServerInfo(self.server_dir + serverName, serverName, serverURL, version=version, serverType=serverType)
            self.addServerItem(serverInfo)
        
        tableWidget.resizeColumnsToContents()
        tableWidget.show()
        
    def addServerItem(self, serverInfo):
        self.servers.append(serverInfo)

        tableWidget = self.tblServer
        tableWidget.setRowCount(tableWidget.rowCount() + 1)
        
        rowCnt = tableWidget.rowCount() - 1
        tableWidget.setItem(rowCnt, 0, QTableWidgetItem(serverInfo.name))
        tableWidget.setItem(rowCnt, 1, QTableWidgetItem(serverInfo.url))
        tableWidget.setItem(rowCnt, 2, QTableWidgetItem(serverInfo.version))
        tableWidget.setItem(rowCnt, 3, QTableWidgetItem(serverInfo.serverType))
        tableWidget.item(rowCnt, 0).setCheckState(QtCore.Qt.Unchecked)
        tableWidget.item(rowCnt, 0).setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable)

    def addServer(self):
        serverName = self.txtName.text()
        serverURL = self.txtURL.text()
        version = self.txtVersion.text()
        serverType = 'General' if self.optGeneral.isChecked() else 'Kopss'
        
        if (not serverName) or (serverName == ""):
            QMessageBox.information(self, u"Information", u'서버 이름은 반드시 입력해야 합니다.')
            return
        
        if (not serverURL) or (serverURL == ""):
            QMessageBox.information(self, u"Information", u'서버 URL은 반드시 입력해야 합니다.')
            return
        
        if (not version) or (version == ""):
            QMessageBox.information(self, u"Information", u'서버 버전은 반드시 입력해야 합니다.')
            return
        
        # check server status
        if self.chekc_server_status(serverURL):
            directory = os.path.join(self.server_dir, serverName)
            if not os.path.exists(directory):
                os.mkdir(directory)
            serverInfo = WpsServerInfo(directory, serverName, serverURL, version=version, serverType=serverType)
            self.addServerItem(serverInfo)
        else:
            QMessageBox.information(self, u"Information", u'올바른 WPS 서버 URL이 아닙니다.')
    
    def chekc_server_status(self, serverURL):
        wps = WebProcessingService(serverURL, verbose=False, skip_caps=True)
        try:
            wps.getcapabilities()
            return 'WPS' == wps.identification.type
        except Exception, e:
            return False
        return False

    def modifyServer(self):
        QMessageBox.information(self, u"Information", u"modifyServer")
    
    def removeServer(self):
        selectedCount = 0
        for row in range(self.tblServer.rowCount()):
            if self.tblServer.item(row, 0).checkState() == QtCore.Qt.Checked:
                selectedCount = selectedCount + 1
                
        if (selectedCount > 0):
            rc = QMessageBox.question(self, u"Confirm", u"선택한 항목을 정말로 삭제하시겠습니까?", QMessageBox.Yes, QMessageBox.No)
            if (rc != QMessageBox.Yes):
                return
                
            # delete server
            for row in range(self.tblServer.rowCount()):
                if self.tblServer.item(row, 0).checkState() == QtCore.Qt.Checked:
                    serverName = self.tblServer.item(row, 0).text()
                    configFile = os.path.join(self.server_dir, serverName + ".ini")
                    if os.path.isfile(configFile):
                        # delete configuration file
                        os.remove(configFile)
                        # delete metadata directory
                        shutil.rmtree(os.path.join(self.server_dir, serverName), ignore_errors=True)
                        # remove item
                        self.tblServer.removeRow(row)
    
    def apply(self):
        for row in range(self.tblServer.rowCount()):
            serverName = self.tblServer.item(row, 0).text()
            serverURL = self.tblServer.item(row, 1).text()
            version = self.tblServer.item(row, 2).text()
            serverType = self.tblServer.item(row, 3).text()
            
            # add new wps server
            # - create folder
            directory = os.path.join(self.server_dir, serverName)
            if not os.path.exists(directory):
                os.mkdir(directory)

            # write configuration file
            serverInfo = WpsServerInfo(directory, serverName, serverURL, version=version, serverType=serverType)
            serverInfo.save()
            # write get caps
        self.accept()
    
    def cancel(self):
        self.close()

