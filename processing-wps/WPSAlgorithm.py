# -*- coding: utf-8 -*-

"""
***************************************************************************
    WPSAlgorithm.py
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

import os, sys, collections, codecs
import traceback
from time import sleep

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.utils import iface

import processing

from processing.core.parameters import ParameterRaster
from processing.core.parameters import ParameterTable
from processing.core.parameters import ParameterVector
from processing.core.parameters import ParameterMultipleInput
from processing.core.parameters import ParameterString
from processing.core.parameters import ParameterCrs
from processing.core.parameters import ParameterNumber
from processing.core.parameters import ParameterBoolean
from processing.core.parameters import ParameterSelection
from processing.core.parameters import ParameterTableField
from processing.core.parameters import ParameterExtent
from processing.core.parameters import ParameterFile

from processing.core.outputs import OutputTable
from processing.core.outputs import OutputVector
from processing.core.outputs import OutputRaster
from processing.core.outputs import OutputNumber
from processing.core.outputs import OutputString
from processing.core.outputs import OutputHTML
from processing.core.outputs import OutputFile

from processing.core.ProcessingLog import ProcessingLog
from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException
from processing.tools.system import getTempFilenameInTempFolder
from processing.tools import dataobjects, vector

from WPSUtils import WPSUtils
from WPSProcess import *
from GMLEncoder import GMLEncoder
from wps import WebProcessingService, Process, Input, Output
from wps import WFSReferenceFeatureCollection, GMLFeatureCollection, BoundingBoxData
from wps import WKTGeometryData, FilterExpressionData, XMLData


class WPSAlgorithm(GeoAlgorithm):
    # All Processing algorithms should extend the GeoAlgorithm class.

    def __init__(self, group, process):
        # The WPS process that the user will use in the toolbox
        self.process = process
        
        GeoAlgorithm.__init__(self)

        # The branch of the toolbox under which the algorithm will appear
        self.group = group

        # The name that the user will see in the toolbox
        self.name = process.getTitle()
            

    def getIcon(self):
        return QIcon(os.path.dirname(__file__) + '/icons/wps.png')

    def getPostProcessingErrorMessage(self, wrongLayers):
        html = '<p>Oooops! The following output layers could not be \
                open</p><ul>\n'
        for layer in wrongLayers:
            html += '<li>' + layer.description \
                + ': <font size=3 face="Courier New" color="#ff0000">' \
                + layer.value + '</font></li>\n'
        html += '</ul><p>The above files could not be opened, which probably \
                 indicates that they were not correctly produced by the \
                 executed algorithm</p>'
        html += '<p>Checking the log information might help you see why those \
                 layers were not created as expected</p>'
        return html

    def defineCharacteristics(self):
        # WPS Data Inputs
        for key, value in self.process.getDataInputs().iteritems():
            optionalBoolean = value.getMinOccurs() != 1
            required = u' (※)' if value.getMinOccurs() == 1 else u''
            paramIdentifier = value.getIdentifier()
            paramTitle = value.getTitle() + required
            
            if isinstance(value, WPSLiteralData):
                # string, double, int, boolean
                defaultValue = value.getDefaultValue()
                param = None
                if value.getType() == LiteralType.BOOLEAN:
                    param = ParameterBoolean(paramIdentifier, paramTitle)
                elif value.getType() == LiteralType.FLOAT:
                    param = ParameterNumber(paramIdentifier, paramTitle)
                    param.isInteger = False
                elif value.getType() == LiteralType.INT:
                    param = ParameterNumber(paramIdentifier, paramTitle)
                    param.isInteger = True
                else:
                    if value.getAllowedValues():
                        param = ParameterSelection2(paramIdentifier, paramTitle, value.getAllowedValues())
                    else:
                        param = ParameterString(paramIdentifier, paramTitle, optional=optionalBoolean)

                if defaultValue:
                    param.setValue(defaultValue)

                self.addParameter(param)
            elif isinstance(value, WPSComplexData):
                # geometry, featurecollection, gridcoverage, xml
                param = None
                if value.getType() == ComplexType.VECTOR:
                    # select vector layer
                    param = ParameterVector(paramIdentifier, paramTitle, optional=optionalBoolean)
                elif value.getType() == ComplexType.RASTER:
                    # select raster layer
                    param = ParameterRaster(paramIdentifier, paramTitle, optional=optionalBoolean)
                elif value.getType() == ComplexType.GEOMETRY:
                    # use WKT format
                    param = ParameterString(paramIdentifier, paramTitle, multiline=True, optional=optionalBoolean)
                elif value.getType() == ComplexType.FILTER:
                    # use ECQL expression
                    param = ParameterString(paramIdentifier, paramTitle, multiline=True, optional=optionalBoolean)
                elif value.getType() == ComplexType.XML:
                    # use XML Expression
                    param = ParameterString(paramIdentifier, paramTitle, multiline=True, optional=optionalBoolean)

                self.addParameter(param)
            elif isinstance(value, WPSBoundingBoxData):
                # default = current map layer's minimum extent & crs
                param = ParameterExtent(paramIdentifier, paramTitle)

                # The value is a string in the form "xmin, xmax, ymin, ymax"
                extent = iface.mapCanvas().extent()
                default_extent = str(extent.xMinimum()) + ',' + str(extent.xMaximum()) + ',' \
                    + str(extent.yMinimum()) + ',' + str(extent.yMaximum())
                param.setValue(default_extent)
                self.addParameter(param)

        # WPS Process Outputs
        # OutputString --> OutputHTML
        for key, value in self.process.getProcessOutputs().iteritems():
            if isinstance(value, WPSLiteralOutput):
                # string, float, int, boolean
                self.addOutput(OutputHTML(value.getIdentifier(), value.getTitle()))
            elif isinstance(value, WPSComplexOutput):
                # geometry, featurecollection, gridcoverage, xml
                if value.getType() == ComplexType.VECTOR:
                    self.addOutput(OutputVector(value.getIdentifier(), value.getTitle()))
                elif value.getType() == ComplexType.RASTER:
                    self.addOutput(OutputRaster(value.getIdentifier(), value.getTitle()))
                elif value.getType() == ComplexType.XML:
                    self.addOutput(OutputHTML(value.getIdentifier(), value.getTitle()))
                elif value.getType() == ComplexType.FILTER:
                    self.addOutput(OutputHTML(value.getIdentifier(), value.getTitle()))
                elif value.getType() == ComplexType.GEOMETRY:
                    # return WKT and save shapefile
                    self.addOutput(OutputVector(value.getIdentifier(), value.getTitle()))
    
    def checkParameterValuesBeforeExecuting(self):
        """If there is any check to do before launching the execution
        of the algorithm, it should be done here.

        If values are not correct, a message should be returned
        explaining the problem.

        This check is called from the parameters dialog, and also when
        calling from the console.
        """

        check_msg = None
        # def setParameterValue(self, paramName, value):
        for key, value in self.process.getDataInputs().iteritems():
            param_value = str(self.getParameterValue(value.getIdentifier()))
            if str(value.getMinOccurs()) == "1":
                if param_value is None or len(param_value) == 0:
                   check_msg = value.getTitle().encode('utf8') +  u" parameter value required!"

        return check_msg

    def execute(self, progress, model=None):
        """The method to use to call a processing algorithm.

        Although the body of the algorithm is in processAlgorithm(),
        it should be called using this method, since it performs
        some additional operations.

        Raises a GeoAlgorithmExecutionException in case anything goe
        wrong.
        """
        self.model = model
        try:
            self.setOutputCRS()
            self.resolveTemporaryOutputs()
            self.checkOutputFileExtensions()
            self.runPreExecutionScript(progress)
            self.processAlgorithm(progress)
            self.convertUnsupportedFormats(progress)
            self.runPostExecutionScript(progress)
        except GeoAlgorithmExecutionException, gaee:
            ProcessingLog.addToLog(ProcessingLog.LOG_ERROR, gaee.msg)
            raise gaee
        except Exception, e:
            # If something goes wrong and is not caught in the
            # algorithm, we catch it here and wrap it
            lines = [u'Uncaught error while executing algorithm']
            errstring = traceback.format_exc()
            newline = errstring.find('\n')
            if newline != -1:
                lines.append(errstring[:newline])
            else:
                lines.append(errstring)
            lines.append(errstring.replace('\n', '|'))
            ProcessingLog.addToLog(ProcessingLog.LOG_ERROR, lines)
            raise GeoAlgorithmExecutionException(str(e)
                    + u'\n Please see the Log for more details')

    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""
        # 1. build request statement
        # 1.1 DataInputs
        data_inputs = []
        for key, value in self.process.getDataInputs().iteritems():
            param_value = str(self.getParameterValue(value.getIdentifier()))
            if param_value is None or len(param_value) == 0:
                continue

            if isinstance(value, WPSLiteralData):
                if value.getType() == LiteralType.STRING and value.getAllowedValues() is None:
                    data_inputs.append((value.getIdentifier(), param_value.encode('utf8')))
                if value.getType() == LiteralType.STRING and value.getAllowedValues():
                    param_value = value.getAllowedValues()[int(param_value)]
                    data_inputs.append((value.getIdentifier(), param_value.encode('utf8')))
                elif value.getType() == LiteralType.INT:
                    data_inputs.append((value.getIdentifier(), param_value.encode('utf8')))
                elif value.getType() == LiteralType.FLOAT:
                    data_inputs.append((value.getIdentifier(), param_value.encode('utf8')))
            elif isinstance(value, WPSComplexData):
                if value.getType() == ComplexType.VECTOR:
                    # local layer = shapefile, gml, json.....
                    layer = dataobjects.getObjectFromUri(param_value)
                    gml_encoder = GMLEncoder(layer, value.getIdentifier())
                    gml_path = gml_encoder.encode('3.1.1')
                    ref_value = GMLFeatureCollection(gml_path, 'text/xml; subtype=gml/3.1.1')
                    data_inputs.append((value.getIdentifier(), ref_value))
                elif value.getType() == ComplexType.RASTER:
                    if os.path.isfile(param_value):
                        raster_layer = dataobjects.getObjectFromUri(param_value)
                    else:
                        ref_value = WFSReferenceFeatureCollection(param_value)
                        data_inputs.append((value.getIdentifier(), ref_value))
                elif value.getType() == ComplexType.GEOMETRY: 
                    ref_value = WKTGeometryData(param_value)
                    data_inputs.append((value.getIdentifier(), ref_value))
                elif value.getType() == ComplexType.FILTER:
                    ref_value = FilterExpressionData(param_value)
                    data_inputs.append((value.getIdentifier(), ref_value))
                elif value.getType() == ComplexType.XML:
                    ref_value = XMLData(param_value)
                    data_inputs.append((value.getIdentifier(), ref_value))
            elif isinstance(value, WPSBoundingBoxData):
                crs = iface.mapCanvas().mapRenderer().destinationCrs()
                ref_value = BoundingBoxData(param_value, crs.authid())
                data_inputs.append((value.getIdentifier(), ref_value))
        
        # 1.2 ProcessOutputs
        process_outputs = []
        for key, value in self.process.getProcessOutputs().iteritems():
            #output_value = self.getOutputValue(value.getIdentifier())
            if isinstance(value, WPSLiteralOutput):
                process_outputs.append((value.getIdentifier(), 'text/xml'))
            elif isinstance(value, WPSComplexOutput):
                if value.getType() == ComplexType.VECTOR:
                    process_outputs.append((value.getIdentifier(), 'text/xml; subtype=gml/3.1.1'))
                elif value.getType() == ComplexType.RASTER:
                    process_outputs.append((value.getIdentifier(), 'image/tiff'))
                elif value.getType() == ComplexType.GEOMETRY:
                    process_outputs.append((value.getIdentifier(), 'application/wkt'))
                elif value.getType() == ComplexType.FILTER:
                    process_outputs.append((value.getIdentifier(), 'text/xml; subtype=filter/1.0'))
                elif value.getType() == ComplexType.XML:
                    process_outputs.append((value.getIdentifier(), 'text/xml'))

        # 2. execute process
        #execute(self, identifier, inputs, output=None, request=None, response=None):
        wps = WebProcessingService(self.process.getServerURL(), verbose=False, skip_caps=True)
        execution = wps.execute(self.process.getIdentifier(), data_inputs, process_outputs)
        
        while execution.isComplete()==False:
            execution.checkStatus(sleepSecs=3)
            print 'Execution status: %s' % execution.status
        
        if execution.isSucceded():
            for output in execution.processOutputs:
                output_value = self.getOutputValue(output.identifier)
                if output.mimeType is None:
                    output.mimeType = ''

                if 'text/xml' == output.mimeType:
                    # custom xml
                    file_name, file_ext = os.path.splitext(output_value)
                    filepath = file_name + '.xml'
                    #filepath = getTempFilenameInTempFolder(output.identifier + '.xml')
                    execution.getIdentifierOutput(output.identifier, filepath)
                    self.setOutputValue(output.identifier, filepath)
                elif 'gml' in output.mimeType:
                    # vector data
                    file_name, file_ext = os.path.splitext(output_value)
                    filepath = file_name + '.gml'
                    execution.getIdentifierOutput(output.identifier, filepath)
                    self.setOutputValue(output.identifier, filepath)
                elif 'wkt' in output.mimeType:
                    # geometry data
                    file_name, file_ext = os.path.splitext(output_value)
                    wkt_path = file_name + '.wkt'
                    execution.getIdentifierOutput(output.identifier, wkt_path)

                    filepath = file_name + '.shp'
                    if WPSUtils.create_shapefile_from_WKT(wkt_path, filepath):
                        self.setOutputValue(output.identifier, filepath)
                elif 'image' in output.mimeType:
                    # raster data
                    file_name, file_ext = os.path.splitext(output_value)
                    filepath = file_name + '.tif'
                    execution.getIdentifierOutput(output.identifier, filepath)
                    self.setOutputValue(output.identifier, filepath)
                else:
                    # general text/plain
                    file_name, file_ext = os.path.splitext(output_value)
                    filepath = file_name + '.txt'
                    #filepath = getTempFilenameInTempFolder(output.identifier + '.txt')
                    execution.getIdentifierOutput(output.identifier, filepath)
                    self.setOutputValue(output.identifier, filepath)
        else:
            QMessageBox.information(iface.mainWindow(), 'Information', 
                u'Failed to execute process. Please check network connection status or variable values.')

    def help(self):
        """Returns the path to the help file with the description of
        this algorithm.

        It should be an HTML file. Returns None if there is no help
        file available.
        """
        file_name = self.process.getIdentifier().replace(":", '_')
        folder = os.path.join(os.path.dirname(__file__), "wps_server", "help")
        if not os.path.isdir(folder):
            os.mkdir(folder)

        html_file = os.path.join(folder, file_name + ".html")
        if os.path.isfile(html_file):
            return False, html_file
        
        return False, WPSUtils.write_metadata_as_html(self.process, html_file)
