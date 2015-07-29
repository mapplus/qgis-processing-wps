# -*- coding: utf-8 -*-

"""
***************************************************************************
    WPSCustomAction.py
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

import os

from PyQt4.QtGui import *
from processing.gui.ToolboxAction import ToolboxAction
from processing.algs.ogcwps.ServerManagerDialog import ServerManagerDialog


class WPSServerManagerAction(ToolboxAction):

    def __init__(self, actionName, provider):
        self.name = actionName
        self.group = u'OGC WPS Server'
        self.provider = provider

    def getIcon(self):
        return QIcon(os.path.dirname(__file__) + '/wps.png')

    def execute(self):
        dlg = ServerManagerDialog(self.provider, None)
        if dlg.exec_():
            self.toolbox.updateProvider(self.provider.getName())
