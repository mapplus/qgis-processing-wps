# -*- coding: utf-8 -*-

"""
***************************************************************************
    ProcessingWPSPlugin.py
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

import os
import sys
import inspect
import webbrowser
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import resources_rc

try:
    from processing.core.Processing import Processing
    from WPSAlgorithmProvider import WPSAlgorithmProvider
    processing_installed = True
except:
    processing_installed = False
    
    
class ProcessingWPSPlugin:

    def __init__(self, iface):
        self.iface = iface
        if processing_installed:
            self.provider = WPSAlgorithmProvider()
            
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
            
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        locale_path = os.path.join(self.plugin_dir, "i18n", "wps_{}.qm".format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

    def unload(self):
        if processing_installed:
            Processing.removeProvider(self.provider)

    def initGui(self):
        if processing_installed:
            Processing.addProvider(self.provider)

    def showHelp(self):
        webbrowser.open("https://github.com/mapplus/qgis-processing-wps")