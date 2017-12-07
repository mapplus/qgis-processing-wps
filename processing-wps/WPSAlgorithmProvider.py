# -*- coding: utf-8 -*-

"""
***************************************************************************
    WPSAlgorithmProvider.py
    ---------------------
    Date                 : January 2014
    Copyright            : (C) 2014 by Minpa Lee
    Email                : mapplus at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Minpa Lee'
__date__ = 'January 2014'
__copyright__ = '(C) 2014, Minpa Lee'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os, urllib2
import ConfigParser

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *
from PyQt4 import QtXml
from PyQt4.QtGui import QApplication, QMessageBox

from processing.core.ProcessingLog import ProcessingLog
from processing.core.ProcessingConfig import ProcessingConfig
from processing.core.AlgorithmProvider import AlgorithmProvider
from processing.core.ProcessingConfig import Setting, ProcessingConfig

from WPSUtils import WPSUtils
from WpsServerInfo import WpsServerInfo
from WPSProcess import *
from WPSAlgorithm import WPSAlgorithm
from wps import WebProcessingService, Process, Input, Output
from WPSServerManagerAction import WPSServerManagerAction


class WPSAlgorithmProvider(AlgorithmProvider):

    def __init__(self):
        AlgorithmProvider.__init__(self)

        # Activate provider by default
        self.activate = True

        # Load algorithms
        self.alglist = []
        self.actions = []

    def initializeSettings(self):
        AlgorithmProvider.initializeSettings(self)
        ProcessingConfig.addSetting(Setting(self.getDescription(),
                                    WPSUtils.PROCESSING_MAX_FEATURES,
                                    self.tr("Maximum Features for processing vector layer"),
                                    WPSUtils.getProcessingMaxFeatures()))

    def unload(self):
        AlgorithmProvider.unload(self)
        ProcessingConfig.removeSetting(WPSUtils.PROCESSING_MAX_FEATURES)

    def getName(self):
        return self.tr("WPS")

    def getDescription(self):
        return self.tr("OGC WPS Services")

    def getIcon(self):
        return QIcon(os.path.dirname(__file__) + '/icons/wps.png')
        
    def tr(self, string, context=''):
        if context == '':
            context = 'WPS'
        return QApplication.translate(context, string, None, QApplication.UnicodeUTF8)

    def _loadAlgorithms(self):
        # WPS GetCapabilities
        self.getCapabilities()
        
        self.actions = []
        self.actions.append(WPSServerManagerAction("WPS Server Setting", self))
        
        for alg in self.alglist:
            alg.provider = self

        self.algs = self.alglist

    def getCapabilities(self):
        self.alglist = []

        # load server
        server_dir = os.path.join(os.path.dirname(__file__), "wps_server")
        Config = ConfigParser.ConfigParser()
        for serverName in os.listdir(server_dir):
            path = os.path.join(server_dir, serverName)
            if os.path.isfile(path):
                continue
                
            config_file = os.path.join(server_dir, serverName + ".ini")
            if not os.path.isfile(config_file):
                continue

            Config.read(config_file)
            serverName = Config.get('WPS', 'Name')
            serverURL = Config.get('WPS', 'URL')
            version = Config.get('WPS', 'Version')
            serverType = Config.get('WPS', 'ServerType')
            serverInfo = WpsServerInfo(os.path.join(server_dir, serverName), serverName, serverURL, version=version, serverType=serverType)

            # http://localhost:8080/gxt/ows?service=wps&version=1.0.0&request=GetCapabilities
            file_path = os.path.join(serverInfo.folder, "WPS_GetCapabilities.xml")
            if not os.path.isfile(file_path):
                # Request & save DescribePorcess xml
                WPSUtils.download_capabilities_xml(WPSUtils.getCapabilitiesUrl(serverURL, version), file_path)

            capabilities_xml_file = QFile(file_path)
            if capabilities_xml_file.open(QIODevice.ReadOnly):
                doc = QtXml.QDomDocument()
                if doc.setContent(capabilities_xml_file):
                    root = doc.documentElement()  
                    version = root.attribute("version")
                    
                    # list process
                    processes = doc.elementsByTagName("wps:Process")
                    for i in range(processes.size()):
                        process = processes.item(i).toElement()
                        identifier = self.getElementText(process, "ows:Identifier")
                        title = self.getElementText(process, "ows:Title")
                        abstract = self.getElementText(process, "ows:Abstract")
                        
                        # process group
                        category = "general"
                        if ":" in identifier:
                            category = identifier.split(":")[0].strip()
                            if category == "kopss":
                                category = identifier.split(":")[1].split("_")[0]
                                
                        group = "General"
                        if category in WPSUtils.PROCESS_CATEGORY:
                            group = WPSUtils.PROCESS_CATEGORY[category]

                        # DescribeProcess
                        process_xml_file = os.path.join(serverInfo.folder, identifier.replace(":", '_') + ".xml")
                        if not os.path.isfile(process_xml_file):
                            if serverType != "GeoServer":
                                continue   # custom
                            # Request & save DescribePorcess xml
                            capabilities_url = WPSUtils.getDescribeProcessUrl(serverURL, version, identifier)
                            WPSUtils.download_capabilities_xml(capabilities_url, process_xml_file)
                        
                        if os.path.isfile(process_xml_file):
                            wps_process = self.parce_wps_process(serverInfo.url, identifier, title, abstract, process_xml_file)
                            if wps_process:
                                self.alglist.append(WPSAlgorithm(group, wps_process))
                        
                capabilities_xml_file.close()
    
    def parce_wps_process2(self, serverURL, process_identifier, process_title, process_abstract, process_xml_file):
        wps = WebProcessingService(serverURL, verbose=False, skip_caps=True)
        xml_string = None
        with open(process_xml_file, 'r') as content_file:
            xml_string = content_file.read()
        if xml_string is None:
            return None
        else:
            return wps.describeprocess(process_identifier, xml_string)

    def parce_wps_process(self, serverURL, process_identifier, process_title, process_abstract, process_xml_file):
        wps_process = None
        capabilities_xml_file = QFile(process_xml_file)
        if capabilities_xml_file.open(QIODevice.ReadOnly):
            doc = QtXml.QDomDocument()
            if doc.setContent(capabilities_xml_file):
                root = doc.documentElement()  # ows:ExceptionReport

                wps_process = WPSProcess(serverURL, process_identifier, process_title, process_abstract)

                # DataInputs
                dataInputs_node = doc.elementsByTagName('DataInputs').item(0).toElement()
                data_inputs = dataInputs_node.elementsByTagName("Input")
                for i in range(data_inputs.size()):
                    data_input = data_inputs.item(i).toElement()

                    minOccurs = int(data_input.attribute('minOccurs'))
                    maxOccurs = int(data_input.attribute('maxOccurs'))

                    identifier = self.getElementText(data_input, "ows:Identifier")
                    title = self.getElementText(data_input, "ows:Title")
                    if not WPSUtils.is_number(title[0]):
                        title = str(i + 1) + ". " + title

                    abstract = self.getElementText(data_input, "ows:Abstract")
                    
                    literalNodes = data_input.elementsByTagName("LiteralData")
                    if literalNodes:
                        literalNode = literalNodes.item(0).toElement()

                        # LiteralType = enum(STRING=1, FLOAT=2, INT=3, BOOLEAN=4)
                        dataType = LiteralType.STRING
                        dataType_nodes = literalNode.elementsByTagName("ows:DataType")
                        if dataType_nodes:
                            node_text = dataType_nodes.item(0).toElement().text()
                            dataType = self.get_literal_type(node_text)

                        literal_data = WPSLiteralData(identifier, title, abstract, dataType, minOccurs, maxOccurs)

                        # default value
                        defaultValue_nodes = literalNode.elementsByTagName("DefaultValue")
                        if defaultValue_nodes:
                            defaultValue = defaultValue_nodes.item(0).toElement().text()
                            literal_data.setDefaultValue(defaultValue)

                        # allowed values
                        allowedValues_nodes = literalNode.elementsByTagName("ows:AllowedValues")
                        if allowedValues_nodes:
                            allowedValues_node = allowedValues_nodes.item(0).toElement()
                            value_nodes = allowedValues_node.elementsByTagName('ows:Value')
                            allowedValues = []
                            for i in range(value_nodes.size()):
                                allowedValues.append(value_nodes.item(i).toElement().text())
                            literal_data.setAllowedValues(allowedValues)

                        wps_process.addInput(literal_data)
                    else:
                        is_bbox = data_input.elementsByTagName("BoundingBoxData")
                        if is_bbox:
                            wps_process.addInput(WPSBoundingBoxData(identifier, title, abstract, minOccurs, maxOccurs))
                        else:
                            # check vector, raster, geometry, xml
                            complex_data_node = data_input.elementsByTagName("ComplexData").item(0).toElement()
                            dataType = self.get_identifier_type(complex_data_node)
                            # skip Raster input
                            if dataType == ComplexType.RASTER:
                                return None
                            wps_process.addInput(WPSComplexData(identifier, title, abstract, dataType, minOccurs, maxOccurs))

                # ProcessOutputs
                processOutputs_node = doc.elementsByTagName('ProcessOutputs').item(0).toElement()
                process_outputs = processOutputs_node.elementsByTagName("Output")
                for i in range(process_outputs.size()):
                    process_output = process_outputs.item(i).toElement()
                    identifier = self.getElementText(process_output, "ows:Identifier")
                    title = self.getElementText(process_output, "ows:Title")
                    abstract = self.getElementText(process_output, "ows:Abstract")

                    literal_nodes = process_output.elementsByTagName("LiteralOutput")
                    if literal_nodes:
                        # LiteralType = enum(STRING=1, FLOAT=2, INT=3, BOOLEAN=4)
                        dataType = LiteralType.STRING
                        wps_process.addOutput(WPSLiteralOutput(identifier, title, abstract, dataType))
                    else:
                        complex_data_node = process_output.elementsByTagName("ComplexOutput").item(0).toElement()
                        dataType = self.get_identifier_type(complex_data_node)
                        # Unsupported process like GetMap....
                        if dataType is None or dataType == ComplexType.XML:
                            return None
                        wps_process.addOutput(WPSComplexOutput(identifier, title, abstract, dataType))

            capabilities_xml_file.close()
        else:
           raise GeoAlgorithmExecutionException(u'Cannot open Capabilities file: \r' + \
                   process_xml_file)
               
        return wps_process

    def get_literal_type(self, description):
        if 'double' in description:
            return LiteralType.FLOAT
        elif 'float' in description:
            return LiteralType.FLOAT
        elif 'int' in description:
            return LiteralType.INT
        elif 'short' in description:
            return LiteralType.INT
        elif 'bool' in description:
            return LiteralType.BOOLEAN
        else:
            return LiteralType.STRING

    def get_identifier_type(self, complex_data_node):
        supported_node = complex_data_node.elementsByTagName('Supported').item(0).toElement()
        format_nodes = supported_node.elementsByTagName('Format')
        for i in range(format_nodes.size()):
            format_node = format_nodes.item(i).toElement()
            mime_type_node = format_node.elementsByTagName('MimeType').item(0).toElement()

            # Mime Type
            if 'text/xml' == mime_type_node.text():
                return ComplexType.XML
            elif 'grid' in mime_type_node.text():
                return ComplexType.RASTER
            elif 'tif' in mime_type_node.text():
                return ComplexType.RASTER
            elif 'application/wkt' in mime_type_node.text():
                return ComplexType.GEOMETRY
            elif 'wfs-collection' in mime_type_node.text():
                return ComplexType.VECTOR
            elif 'filter' in mime_type_node.text():
                return ComplexType.FILTER

    def getElementText(self, element, tagName):
        identifiers = element.elementsByTagName(tagName)
        if (identifiers.size() > 0):
            identifier = identifiers.item(0).toElement()
            return identifier.text()
        else:
            return None

