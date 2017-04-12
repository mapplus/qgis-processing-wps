# -*- coding: utf-8 -*-

"""
***************************************************************************
    GMLEncoder.py
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

import os, os.path, codecs

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

import processing
from processing.core.ProcessingConfig import ProcessingConfig
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException
from processing.tools import dataobjects, vector
from processing.tools.system import *
from WPSUtils import WPSUtils


class GMLEncoder:

    def __init__(self, layer, identifier):
        self.layer = layer
        self.identifier = identifier
    
    def encode(self, gml_version=None):
        if gml_version is None:
            return self.encode_gml311(self.layer, self.identifier)
        elif gml_version.startswith('3'):
            return self.encode_gml311(self.layer, self.identifier)
        elif gml_version.startswith('2'):
            return self.encode_gml212(self.layer, self.identifier)
        else:
            return self.encode_gml311(self.layer, self.identifier)

    def encode_gml212(self, layer, identifier):
        use_selected = ProcessingConfig.getSetting(ProcessingConfig.USE_SELECTED)
        if use_selected and layer.selectedFeatureCount() == 0:
            use_selected = False
            processing_count = layer.featureCount()
        elif use_selected and layer.selectedFeatureCount() > 0:
            processing_count = layer.selectedFeatureCount()
        else:
            use_selected = False
            processing_count = layer.featureCount()

        if processing_count > float(WPSUtils.getProcessingMaxFeatures()):
            max_features = str(WPSUtils.getProcessingMaxFeatures())
            raise GeoAlgorithmExecutionException(u"Maximum Features for processing vector layer is " + max_features)
        
        # write gml using ogr driver        
        gml_path = getTempFilenameInTempFolder(identifier + '.gml')
        error = QgsVectorFileWriter.writeAsVectorFormat(layer, gml_path, "utf-8", layer.crs(), "GML", use_selected)
        if error != QgsVectorFileWriter.NoError:
            raise GeoAlgorithmExecutionException(u"Cannot convert to GML object!")
        else:
            return gml_path

    def encode_gml311(self, layer, identifier):
        use_selected = ProcessingConfig.getSetting(ProcessingConfig.USE_SELECTED)
        if use_selected and layer.selectedFeatureCount() == 0:
            use_selected = False
            processing_count = layer.featureCount()
        elif use_selected and layer.selectedFeatureCount() > 0:
            processing_count = layer.selectedFeatureCount()
        else:
            use_selected = False
            processing_count = layer.featureCount()

        if processing_count > float(WPSUtils.getProcessingMaxFeatures()):
            max_features = str(WPSUtils.getProcessingMaxFeatures())
            raise GeoAlgorithmExecutionException(u"Maximum Features for processing vector layer is " + max_features)

        # write to file
        gml_path = getTempFilenameInTempFolder(identifier + '.xml')
        writer = codecs.open(gml_path, 'w', encoding='utf-8')

        # write header
        writer.write('<?xml version="1.0" encoding="UTF-8"?>')
        writer.write('<wfs:FeatureCollection xmlns:feature="http://www.opengis.net/feature" xmlns:ogc="http://www.opengis.net/ogc"  xmlns:gml="http://www.opengis.net/gml"  xmlns:xlink="http://www.w3.org/1999/xlink"  xmlns:ows="http://www.opengis.net/ows"  xmlns:wfs="http://www.opengis.net/wfs">')
        writer.write('<gml:boundedBy>')
        writer.write('<gml:Envelope>')
        extent = layer.extent()
        lowerCorner = str(extent.xMinimum()) + ' ' + str(extent.yMinimum())
        upperCorner = str(extent.xMaximum()) + ' ' + str(extent.yMaximum())
        writer.write('<gml:lowerCorner>' + lowerCorner + '</gml:lowerCorner>')
        writer.write('<gml:upperCorner>' + upperCorner + '</gml:upperCorner>')
        writer.write('</gml:Envelope>')
        writer.write('</gml:boundedBy>')

        # write feature
        crs_id = str(layer.crs().authid()).lower().replace('epsg:', '')
        features = layer.selectedFeatures() if use_selected else layer.getFeatures()
        for feature in features:
            writer.write('<gml:featureMember>')
            writer.write('<feature:' + identifier + ' gml:id="' + identifier + '.' + str(feature.id()) +'">')
            writer.write('<gml:boundedBy>')
            extent = feature.geometry().boundingBox()
            lowerCorner = str(extent.xMinimum()) + ' ' + str(extent.yMinimum())
            upperCorner = str(extent.xMaximum()) + ' ' + str(extent.yMaximum())
            writer.write('<gml:Envelope srsDimension="2" srsName="http://www.opengis.net/gml/srs/epsg.xml#' + crs_id + '">')
            writer.write('<gml:lowerCorner>' + lowerCorner + '</gml:lowerCorner>')
            writer.write('<gml:upperCorner>' + upperCorner + '</gml:upperCorner>')
            writer.write('</gml:Envelope>')
            writer.write('</gml:boundedBy>')

            # write attributes
            for field in feature.fields():
                name = field.name()

                # skip auto generated gml_id_xxx
                if 'gml_id' in name:
                    continue
                
                attribute = feature.attribute(name)
                if attribute:
                    writer.write('<feature:' + name +'>')
                    if field.type() == QVariant.String:
                        writer.write(feature.attribute(name))
                    else:
                        writer.write(str(feature.attribute(name)))
                    writer.write('</feature:' + name +'>')
                else:
                    writer.write('<feature:' + name +' />')
                
            # write geometry
            writer.write('<feature:the_geom>')
            self.write_geometry(writer, feature.geometry(), crs_id)
            writer.write('</feature:the_geom>')

            writer.write('</feature:' + identifier + '>')
            writer.write('</gml:featureMember>')
        writer.write('</wfs:FeatureCollection>')
        writer.close()

        return gml_path

    def write_geometry(self, writer, geometry, crs_id):
        geometryType = 'Point'
        if geometry.wkbType() == QGis.WKBPoint:
            geometryType = 'Point'
        elif geometry.wkbType() == QGis.WKBLineString:
            geometryType = 'MultiLineString'
        elif geometry.wkbType() == QGis.WKBPolygon:
            geometryType = 'MultiPolygon'
        elif geometry.wkbType() == QGis.WKBMultiPoint:
            geometryType = 'MultiPoint'
        elif geometry.wkbType() == QGis.WKBMultiLineString:
            geometryType = 'MultiLineString'
        elif geometry.wkbType() == QGis.WKBMultiPolygon:
            geometryType = 'MultiPolygon'
        
        # write geometry
        srsName = '"http://www.opengis.net/gml/srs/epsg.xml#' + crs_id + '"'
        writer.write('<gml:' + geometryType + ' srsDimension="2" srsName=' + srsName + '>')
        if geometry.wkbType() == QGis.WKBPoint:
            '''
            <gml:Point srsDimension="2" srsName="http://www.opengis.net/gml/srs/epsg.xml#5181">
              <gml:pos>2.079641 45.001795</gml:pos>
            </gml:Point>
            '''
            point = geometry.asPoint()            
            coords = str(point.x()) + ' ' + str(point.y())
            writer.write('  <gml:pos>' + coords + '</gml:pos>')
        elif geometry.wkbType() == QGis.WKBMultiPoint:
            '''
            <gml:MultiPoint srsDimension="2" srsName="http://www.opengis.net/gml/srs/epsg.xml#5181">
              <gml:pointMember>
                <gml:Point>
                  <gml:pos>2.079641 45.001795</gml:pos>
                </gml:Point>
              </gml:pointMember>
              <gml:pointMember>
                <gml:Point>
                  <gml:pos>2.718330 45.541131</gml:pos>
                </gml:Point>
              </gml:pointMember>
            </gml:MultiPoint>
            '''
            self.write_multipoint(writer, geometry.asMultiPoint())
        elif geometry.wkbType() == QGis.WKBLineString:
            # write linestring as multilinestring
            self.write_multilinestring(writer, [geometry.asPolyline()])
        elif geometry.wkbType() == QGis.WKBMultiLineString:
            '''
            <gml:MultiLineString srsDimension="2" srsName="http://www.opengis.net/gml/srs/epsg.xml#5181">
              <gml:lineStringMember>
                <gml:LineString>
                  <gml:posList>379465 187120 379602 187096 ... </gml:posList>
                </gml:LineString>
              </gml:lineStringMember>
            </gml:MultiLineString>
            '''
            self.write_multilinestring(writer, geometry.asMultiPolyline() )
        elif geometry.wkbType() == QGis.WKBPolygon:
            # write polygon as multipolygon
            self.write_multipolygon(writer, [geometry.asPolygon()])
        elif geometry.wkbType() == QGis.WKBMultiPolygon:
            '''
            <gml:MultiPolygon srsDimension="2" srsName="http://www.opengis.net/gml/srs/epsg.xml#5181">
              <gml:polygonMember>
                <gml:Polygon>
                  <gml:exterior>
                    <gml:LinearRing>
                      <gml:posList>189367 446360 189369 446668 ...</gml:posList>
                    </gml:LinearRing>
                  </gml:exterior>
                  <gml:interior>
                    <gml:LinearRing>
                      <gml:posList>189367 446360 189369 446668 ...</gml:posList>
                    </gml:LinearRing>
                  </gml:interior>
                </gml:Polygon>
              </gml:polygonMember>
            </gml:MultiPolygon>
            '''
            self.write_multipolygon(writer, geometry.asMultiPolygon())

        writer.write('</gml:' + geometryType + '>')


    def write_multipoint(self, writer, multiPoint):
        for point in multiPoint:
            writer.write('<gml:pointMember>')
            writer.write('<gml:Point>')
            coords = str(point.x()) + ' ' + str(point.y())
            writer.write('<gml:pos>' + coords + '</gml:pos>')
            writer.write('</gml:Point>')
            writer.write('</gml:pointMember>')


    def write_multilinestring(self, writer, multiLineString):
        for lineString in multiLineString:
            writer.write('<gml:lineStringMember>')
            writer.write('<gml:LineString>')
            posList = self.getPosList(lineString)
            writer.write('<gml:posList>' + posList + '</gml:posList>')
            writer.write('</gml:LineString>')
            writer.write('</gml:lineStringMember>')


    def write_multipolygon(self, writer, multiPolygon):
        for polygon in multiPolygon:
            writer.write('<gml:polygonMember>')
            writer.write('<gml:Polygon>')
            for i in range(len(polygon)):
                linearRing = polygon[i]
                ring_type = 'exterior' if i == 0 else 'interior'

                writer.write('<gml:' + ring_type + '>')
                writer.write('<gml:LinearRing>')
                posList = self.getPosList(linearRing)
                writer.write('<gml:posList>' + posList + '</gml:posList>')
                writer.write('</gml:LinearRing>')
                writer.write('</gml:' + ring_type + '>')
            writer.write('</gml:Polygon>')
            writer.write('</gml:polygonMember>')


    def getPosList(self, geometry):
        posList = []
        for point in geometry:
            posList.append(str(point.x()) + ' ' + str(point.y()))
        return ' '.join(posList)
