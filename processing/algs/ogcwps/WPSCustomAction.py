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
from processing.algs.ogcwps.CreateMDADatasetDialog import CreateMDADatasetDialog


class WPSCustomAction(ToolboxAction):

    MDA = 0
    OTHER = 9999

    def __init__(self, actionName, scriptType):
        self.name = actionName
        self.group = u'도구 - 분석지표 추출'
        self.scriptType = scriptType

    def getIcon(self):
        if self.scriptType == self.MDA:
            return QIcon(os.path.dirname(__file__) + '/wps.png')
        elif self.scriptType == self.OTHER:
            return QIcon(os.path.dirname(__file__) + '/wps.png')

    def execute(self):
        dlg = None
        if self.scriptType == self.MDA:
            dlg = CreateMDADatasetDialog(None)

        dlg.exec_()
