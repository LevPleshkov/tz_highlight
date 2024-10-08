# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TZHighlight
                                 A QGIS plugin
 Highlights UTC timezone by selected object
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-11-15
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Irina Ogorodova
        email                : ogorodova@mail.ru
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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import QAction
# Initialize Qt resources from file resources.py
from .resources import *

# Import the code for the DockWidget
from .tz_highlight_dockwidget import TZHighlightDockWidget
import os.path

from qgis.gui import QgsHighlight
import tz_highlight.map_tool as mt

import pandas as pd


class TZHighlight:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'TZHighlight_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Time Zone Highlighter')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'TZHighlight')
        self.toolbar.setObjectName(u'TZHighlight')

        #print "** INITIALIZING TZHighlight"

        self.pluginIsActive = False
        self.dockwidget = None

        self.map_canvas = self.iface.mapCanvas()
        self.active_layer = self.iface.activeLayer()

        self.codes = None
        self.highlighter = None
        self.timezones = None
        self.highlights = []


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('TZHighlight', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/tz_highlight/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'TZ Highlight'),
            callback=self.run,
            parent=self.iface.mainWindow())

    # --------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        #print "** CLOSING TZHighlight"

        self.map_canvas.unsetMapTool(self.highlighter)
        self.clear_highlights()

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        #print "** UNLOAD TZHighlight"

        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Time Zone Highlighter'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    # --------------------------------------------------------------------------

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            #print "** STARTING TZHighlight"

            self.setup_plugin()

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget == None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = TZHighlightDockWidget()

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.TopDockWidgetArea, self.dockwidget)            
            self.dockwidget.show()

    # --------------------------------------------------------------------------

    def setup_plugin(self):
        if not self.active_layer:
            return

        self.codes = self.load_codes()

        self.highlighter = mt.Highlighter(canvas=self.map_canvas, layer=self.active_layer)
        self.highlighter.featureSelected.connect(self.hightlight)
        self.map_canvas.setMapTool(self.highlighter)

        # self.timezones = self.load_codes()


    def hightlight(self):
        selected_feature = self.highlighter.feature
        if not selected_feature:
            return

        tzid = selected_feature['TZID']
        utc = self.codes.loc[self.codes.TZID == tzid].index

        if not len(utc):
            return

        self.dockwidget.label.setText(f'<html><head/><body><p><span style=" font-size:18pt;">UTC {utc[0]}</span></p></body></html>')

        timezones = self.codes.loc[self.codes.index == utc[0]].to_numpy()

        self.clear_highlights()
        outline_color = QColor(Qt.red)
        fill_color = outline_color
        fill_color.setAlpha(50)

        for feature in self.active_layer.getFeatures():
            if feature['TZID'] in timezones:
                highlight = QgsHighlight(self.map_canvas, feature, self.active_layer)
                highlight.setColor(outline_color)
                highlight.setFillColor(fill_color)
                highlight.show()
                self.highlights.append(highlight)

    
    def clear_highlights(self):
        for hl in self.highlights:
            hl.hide()
        self.highlights = []


    def load_codes(self):
        return pd.read_csv('/Users/levpleshkov/Developer/QGIS/Highlight Timezone/tz_highlight/codes.csv', index_col=1)
