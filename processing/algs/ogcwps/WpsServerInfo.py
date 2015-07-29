# -*- coding: utf-8 -*-
"""
/***************************************************************************
    WpsServerInfo.py
    ---------------------
    Date                 : January 2015
    Copyright            : (C) 2015 by Minpa Lee
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
__date__ = 'April 2015'
__copyright__ = '(C) 2015, Minpa Lee'

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


class WpsServerInfo:

    def __init__(self, folder, name, url, version="1.0.0", serverType="General"):
        self.folder = folder
        self.name = name
        self.url = url
        self.version = version
        self.serverType = serverType

    def save(self):
        # write ini file
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        
        server_dir = os.path.join(os.path.dirname(__file__), "wps_server")
        Config = ConfigParser.ConfigParser()
        cfgfile = open(os.path.join(server_dir, self.name + ".ini"),'w') 

        Config.add_section('WPS')
        Config.set('WPS','Name', self.name)
        Config.set('WPS','URL', self.url)
        Config.set('WPS','Version', self.version)
        Config.set('WPS','ServerType', self.serverType)
        Config.write(cfgfile)
        cfgfile.close()