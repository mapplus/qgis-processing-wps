# -*- coding: utf-8 -*-

"""
***************************************************************************
    WPSUtils.py
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

import os, os.path, codecs, urllib2

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.utils import iface

import processing
from processing.core.ProcessingConfig import ProcessingConfig
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException
from processing.tools import dataobjects, vector
from processing.tools.system import *
from owslib.etree import etree


class WPSUtils:
    PROCESS_CATEGORY = {'general': u"General Processes",
                'geo': u"Geometry Operator",
                'vec': u"Vector Analysis",
                'ras': u"Raster Analysis",
                'gs': u"GeoServer Process",
                'groovy': u"Scripting Extension",
                'py': u"Scripting Extension",
                'gt': u"GeoTools Analysis",
                'JTS': u"Geometry Operator", 
                'kopss': u"Domain Specific Analysis", 
                'KM': u"Domain Specific Analysis",
                'VA': u"Vector Analysis", 
                'CA': u"Raster Analysis", 
                'SA': u"Statistics(Spatial) Analysis", 
                'ST': u"Geometry Operator",
                'statistics': u"Statistics(Spatial) Analysis",
                'CM': u"Domain Specific Analysis"}

    PROCESSING_MAX_FEATURES = 'PROCESSING_MAX_FEATURES'

    @staticmethod
    def getCapabilitiesUrl(serverURL, version):
       return serverURL + "?service=wps&version=" + version  + "&request=GetCapabilities"

    @staticmethod
    def getDescribeProcessUrl(serverURL, version, identifier):
       return serverURL + "?service=wps&version=" + version + "&request=DescribeProcess&identifier=" + identifier

    @staticmethod
    def getProcessingMaxFeatures():
        max_features = ProcessingConfig.getSetting(WPSUtils.PROCESSING_MAX_FEATURES)
        if max_features is None:
            return 500  # default
        else:
            return max_features

    @staticmethod
    def is_number(value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def download_capabilities_xml(url, target_file):
        try:
            response = urllib2.urlopen(url)
            local_file = open(target_file, "w")
            local_file.write(response.read())
            local_file.close()
        except urllib2.HTTPError:
            print("HTTPERROR!")
        except urllib2.URLError:
            print("URLERROR!")

    @staticmethod
    def create_shapefile_from_WKT(wktFile, outputShapefile):
        with codecs.open(wktFile, 'r', "utf-8") as content_file:
            wkt = content_file.read()

            settings = QSettings()
            encoding = settings.value('/UI/encoding', 'System')

            geometry = QgsGeometry.fromWkt(wkt)

            fields = QgsFields()
            fields.append(QgsField("geom_id", QVariant.Int))
            crs = iface.mapCanvas().mapRenderer().destinationCrs()
            writer = QgsVectorFileWriter(outputShapefile, encoding, fields,
                    geometry.wkbType(), crs)

            feature = QgsFeature(fields)
            feature.setGeometry( geometry )
            feature.setAttributes([1])
            writer.addFeature(feature)

            del writer

            return outputShapefile

    @staticmethod
    def write_metadata_as_html(process, html_file):        
        font_family = '"Lucida Sans", "Lucida Sans Unicode", "Lucida Grande", "Verdana", "Arial", "Helvetica", "sans-serif"'

        writer = codecs.open(html_file, 'w', encoding='utf-8')
        writer.write('<html>\r')
        writer.write('<head>\r')
        writer.write('  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\r')
        writer.write('  <title>' + process.getTitle() + '</title>\r')
        writer.write('  <style type="text/css">\r')
        writer.write('    body {\r')
        writer.write('      font-size:11pt;\r')
        writer.write('      font-family: ' + font_family + ';\r')
        writer.write('      background-color: #ffffff }\r')
        writer.write('    h1 {\r')
        writer.write('      font-size:11pt;\r')
        writer.write('      font-family: ' + font_family + '; }\r')
        writer.write('    table, th, td {\r')
        writer.write('      font-size:10pt;\r')
        writer.write('      vertical-align:center;\r')
        writer.write('      border-collapse:collapse;\r')
        writer.write('      padding:0px; border-spacing:0px;\r')
        writer.write('      font-family: ' + font_family + '; }\r')
        writer.write('  </style>\r')
        writer.write('</head>\r')
        writer.write('<body>\r')

        #0. process description
        writer.write(process.getAbstract() + "\r")
        
        #1. input
        writer.write('<h1>Input Parameters</h1>\r')
        writer.write('<table width="100%" border="1" rules="none" frame="hsides">\r')
        writer.write('  <colgroup>\r')
        writer.write('    <col width="30%" />\r')
        writer.write('    <col width="60%" />\r')
        writer.write('    <col width="10%" />\r')
        writer.write('  </colgroup>\r')
        writer.write('  <tr bgcolor="#cccccc">\r')
        writer.write('    <td><strong>Parameter</strong></td>\r')
        writer.write('    <td><strong>Explanation</strong></td>\r')
        writer.write('    <td><strong>Required</strong></td>\r')
        writer.write('  </tr>\r')
        for key, value in process.getDataInputs().iteritems():
            required = 'true' if str(value.getMinOccurs()) == "1" else 'false'
            writer.write('  <tr>\r')
            writer.write('    <td>' + value.getTitle() + '</td>\r')
            writer.write('    <td>' + value.getAbstract() + '</td>\r')
            writer.write('    <td>' +  required + '</td>\r')
            writer.write('  </tr>\r')
        writer.write('</table>\r')

        #2. output
        writer.write('<h1>Output Parameters</h1>\r')
        writer.write('<table width="100%" border="1" rules="none" frame="hsides">\r')
        writer.write('  <colgroup>\r')
        writer.write('    <col width="30%" />\r')
        writer.write('    <col width="60%" />\r')
        writer.write('    <col width="10%" />\r')
        writer.write('  </colgroup>\r')
        writer.write('  <tr bgcolor="#cccccc">\r')
        writer.write('    <td><strong>Parameter</strong></td>\r')
        writer.write('    <td><strong>Explanation</strong></td>\r')
        writer.write('  </tr>\r')
        for key, value in process.getProcessOutputs().iteritems():
            writer.write('  <tr>\r')
            writer.write('    <td>' + value.getTitle() + '</td>\r')
            writer.write('    <td>' + value.getAbstract() + '</td>\r')
            writer.write('  </tr>\r')
        writer.write('</table>\r')
        writer.write('</body>\r')
        writer.write('</html>\r')
        writer.close()

        return html_file