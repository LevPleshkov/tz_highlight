from qgis.PyQt.QtCore import pyqtSignal

from qgis.core import QgsVectorLayer, QgsFeature, QgsPointXY
from qgis.gui import QgsMapCanvas, QgsMapMouseEvent, QgsMapTool


class Highlighter(QgsMapTool):

    featureSelected = pyqtSignal(name='featureSelected')

    def __init__(self, canvas: QgsMapCanvas, layer: QgsVectorLayer) -> None:
        super().__init__(canvas)
        self.layer: QgsVectorLayer = layer
        self.feature: QgsFeature = None

    def canvasPressEvent(self, e: QgsMapMouseEvent) -> None:
        cursor_pos: QgsPointXY = self.toMapCoordinates(e.pos())
        for feature in self.layer.getFeatures():
            if feature.geometry().contains(cursor_pos):
                self.feature = feature
                self.featureSelected.emit()
                break
