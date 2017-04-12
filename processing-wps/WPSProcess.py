# -*- coding: utf-8 -*-

"""
***************************************************************************
    WPSProcess.py
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

import collections
from collections import namedtuple
from processing.core.parameters import Parameter, ParameterSelection

def enum(**enums):
    return type('Enum', (object,), enums)

LiteralType = enum(STRING=1, FLOAT=2, INT=3, BOOLEAN=4)
ComplexType = enum(VECTOR=1, RASTER=2, GEOMETRY=3, XML=4, FILTER=5)


class WPSProcess:
    #DataInputs = {}        # identifier, WPSDataType
    #ProcessOutputs = {}    # identifier, WPSDataType

    def __init__(self, serverURL, identifier, title, abstract=None):
        self.serverURL = serverURL
        self.identifier = identifier
        self.title = title
        self.abstract = abstract
        self.DataInputs = {}
        self.ProcessOutputs = {}
    
    def getServerURL(self):
        return self.serverURL
    
    def getIdentifier(self):
        return self.identifier
    
    def getTitle(self):
        return self.title
    
    def getAbstract(self):
        return self.abstract
    
    def getDataInputs(self):
        return collections.OrderedDict(sorted(self.DataInputs.items()))
    
    def getProcessOutputs(self):
        return collections.OrderedDict(sorted(self.ProcessOutputs.items()))

    def addInput(self, dataInput):
        self.DataInputs[dataInput.getTitle()] = dataInput

    def addOutput(self, processOutput):
        self.ProcessOutputs[processOutput.getTitle()] = processOutput


class WPSDataType:

    def __init__(self, identifier, title, abstract=None, minOccurs=0, maxOccurs=1):
        self.identifier = identifier
        self.title = title
        self.abstract = abstract
        self.minOccurs = minOccurs  # if 1, mandatory parameter
        self.maxOccurs = maxOccurs
        self.allowedValues = None
        self.defaultValue = None
    
    def getIdentifier(self):
        return self.identifier
    
    def getTitle(self):
        return self.title
    
    def getAbstract(self):
        return '' if self.abstract is None else self.abstract

    def setDefaultValue(self, defaultValue):
        self.defaultValue = defaultValue
    
    def getDefaultValue(self):
        return self.defaultValue

    def setMinOccurs(self, minOccurs):
        self.minOccurs = minOccurs
    
    def getMinOccurs(self):
        return self.minOccurs

    def setMaxOccurs(self, maxOccurs):
        self.maxOccurs = maxOccurs
    
    def getMaxOccurs(self):
        return self.maxOccurs

    def setAllowedValues(self, allowedValues):
        #allowedValues = ['upper', 'lower']
        self.allowedValues = allowedValues
    
    def getAllowedValues(self):
        return self.allowedValues


class WPSLiteralData(WPSDataType):
    # string, float, int, boolean

    def __init__(self, identifier, title, abstract=None, dataType=LiteralType.STRING, minOccurs=0, maxOccurs=1):
        self.dataType = dataType
        WPSDataType.__init__(self, identifier, title, abstract, minOccurs, maxOccurs)
    
    def getType(self):
        return self.dataType


class WPSComplexData(WPSDataType):
    # geometry, featurecollection, gridcoverage, xml

    def __init__(self, identifier, title, abstract=None, dataType=ComplexType.VECTOR, minOccurs=0, maxOccurs=1):
        self.dataType = dataType
        WPSDataType.__init__(self, identifier, title, abstract, minOccurs, maxOccurs)
    
    def getType(self):
        return self.dataType


class WPSBoundingBoxData(WPSDataType):
    # boundingbox

    def __init__(self, identifier, title, abstract=None, minOccurs=0, maxOccurs=1):
        WPSDataType.__init__(self, identifier, title, abstract, minOccurs, maxOccurs)


class WPSLiteralOutput(WPSDataType):

    def __init__(self, identifier, title, abstract=None, dataType=LiteralType.STRING):
        self.dataType = dataType
        WPSDataType.__init__(self, identifier, title, abstract)
    
    def getType(self):
        return self.dataType


class WPSComplexOutput(WPSDataType):

    def __init__(self, identifier, title, abstract=None, dataType=ComplexType.VECTOR):
        self.dataType = dataType
        WPSDataType.__init__(self, identifier, title, abstract)
    
    def getType(self):
        return self.dataType


class ParameterSelection2(ParameterSelection):

    def __init__(self, name='', description='', options=[], default=0):
        Parameter.__init__(self, name, description)
        self.options = options
        if isinstance(self.options, basestring):
            self.options = self.options.split(";")
        self.value = None
        self.default = int(default)

    def setValue(self, n):
        if n is None:
            self.value = self.default
            return True
        try:
            n = int(n)
            self.value = n
            return True
        except:
            return False

    def getValueAsCommandLineParameter(self):
        return '"' + unicode(self.options[self.value]) + '"'

