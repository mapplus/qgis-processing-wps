# -*- coding: utf-8 -*-

"""
***************************************************************************
    hugeFileGroundClassify.py
    ---------------------
    Date                 : May 2014
    Copyright            : (C) 2014 by Martin Isenburg
    Email                : martin near rapidlasso point com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Martin Isenburg'
__date__ = 'May 2014'
__copyright__ = '(C) 2014, Martin Isenburg'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

import os
from LAStoolsUtils import LAStoolsUtils
from LAStoolsAlgorithm import LAStoolsAlgorithm

from processing.core.parameters import ParameterBoolean
from processing.core.parameters import ParameterSelection
from processing.core.parameters import ParameterNumber


class hugeFileGroundClassify(LAStoolsAlgorithm):

    TILE_SIZE = "TILE_SIZE"
    BUFFER = "BUFFER"
    AIRBORNE = "AIRBORNE"
    TERRAIN = "TERRAIN"
    TERRAINS = ["wilderness", "nature", "town", "city", "metro"]
    GRANULARITY = "GRANULARITY"
    GRANULARITIES = ["coarse", "default", "fine", "extra_fine", "ultra_fine"]

    def defineCharacteristics(self):
        self.name, self.i18n_name = self.trAlgorithm('hugeFileGroundClassify')
        self.group, self.i18n_group = self.trAlgorithm('LAStools Pipelines')
        self.addParametersPointInputGUI()
        self.addParameter(ParameterNumber(
            hugeFileGroundClassify.TILE_SIZE,
            self.tr("tile size (side length of square tile)"),
            0, None, 1000.0))
        self.addParameter(ParameterNumber(hugeFileGroundClassify.BUFFER,
                                          self.tr("buffer around each tile (avoids edge artifacts)"),
                                          0, None, 25.0))
        self.addParameter(ParameterBoolean(hugeFileGroundClassify.AIRBORNE,
                                           self.tr("airborne LiDAR"), True))
        self.addParameter(ParameterSelection(hugeFileGroundClassify.TERRAIN,
                                             self.tr("terrain type"), hugeFileGroundClassify.TERRAINS, 1))
        self.addParameter(ParameterSelection(hugeFileGroundClassify.GRANULARITY,
                                             self.tr("preprocessing"), hugeFileGroundClassify.GRANULARITIES, 1))
        self.addParametersTemporaryDirectoryGUI()
        self.addParametersPointOutputGUI()
        self.addParametersCoresGUI()
        self.addParametersVerboseGUI()

    def processAlgorithm(self, progress):

        # first we tile the data with option '-reversible'
        commands = [os.path.join(LAStoolsUtils.LAStoolsPath(), "bin", "lastile")]
        self.addParametersVerboseCommands(commands)
        self.addParametersPointInputCommands(commands)
        tile_size = self.getParameterValue(hugeFileGroundClassify.TILE_SIZE)
        commands.append("-tile_size")
        commands.append(unicode(tile_size))
        buffer = self.getParameterValue(hugeFileGroundClassify.BUFFER)
        if buffer != 0.0:
            commands.append("-buffer")
            commands.append(unicode(buffer))
        commands.append("-reversible")
        self.addParametersTemporaryDirectoryAsOutputDirectoryCommands(commands)
        commands.append("-o")
        commands.append("hugeFileGroundClassify.laz")

        LAStoolsUtils.runLAStools(commands, progress)

        # then we ground classify the reversible tiles
        commands = [os.path.join(LAStoolsUtils.LAStoolsPath(), "bin", "lasground")]
        self.addParametersVerboseCommands(commands)
        self.addParametersTemporaryDirectoryAsInputFilesCommands(commands, "hugeFileGroundClassify*.laz")
        airborne = self.getParameterValue(hugeFileGroundClassify.AIRBORNE)
        if not airborne:
            commands.append("-not_airborne")
        method = self.getParameterValue(hugeFileGroundClassify.TERRAIN)
        if method != 1:
            commands.append("-" + hugeFileGroundClassify.TERRAINS[method])
        granularity = self.getParameterValue(hugeFileGroundClassify.GRANULARITY)
        if granularity != 1:
            commands.append("-" + hugeFileGroundClassify.GRANULARITIES[granularity])
        self.addParametersTemporaryDirectoryAsOutputDirectoryCommands(commands)
        commands.append("-odix")
        commands.append("_g")
        commands.append("-olaz")
        self.addParametersCoresCommands(commands)

        LAStoolsUtils.runLAStools(commands, progress)

        # then we reverse the tiling
        commands = [os.path.join(LAStoolsUtils.LAStoolsPath(), "bin", "lastile")]
        self.addParametersVerboseCommands(commands)
        self.addParametersTemporaryDirectoryAsInputFilesCommands(commands, "hugeFileGroundClassify*_g.laz")
        commands.append("-reverse_tiling")
        self.addParametersPointOutputCommands(commands)

        LAStoolsUtils.runLAStools(commands, progress)
