from typing import Any, Tuple

from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsSingleSymbolRenderer,
)
from qgistim.core.elements.colors import BLACK
from qgistim.core.elements.element import ElementExtraction, TransientElement
from qgistim.core.elements.schemata import SingleRowSchema
from qgistim.core.schemata import AllRequired, Positive, Required, StrictlyIncreasing


class DomainSchema(SingleRowSchema):
    timml_schemata = {"geometry": Required()}
    timeseries_schemata = {
        "time": AllRequired(Positive(), StrictlyIncreasing()),
    }


class Domain(TransientElement):
    element_type = "Domain"
    geometry_type = "Polygon"
    ttim_attributes = (QgsField("time", QVariant.Double),)
    schema = DomainSchema()

    def __init__(self, path: str, name: str):
        self._initialize_default(path, name)
        self.timml_name = f"timml {self.element_type}:Domain"
        self.ttim_name = "ttim Computation Times:Domain"

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        """
        Results in transparent fill, with a medium thick black border line.
        """
        return cls.polygon_renderer(
            color="255,0,0,0", color_border=BLACK, width_border="0.75"
        )

    def remove_from_geopackage(self):
        pass

    def update_extent(self, iface: Any) -> Tuple[float, float]:
        provider = self.timml_layer.dataProvider()
        provider.truncate()  # removes all features
        canvas = iface.mapCanvas()
        extent = canvas.extent()
        xmin = extent.xMinimum()
        ymin = extent.yMinimum()
        xmax = extent.xMaximum()
        ymax = extent.yMaximum()
        points = [
            QgsPointXY(xmin, ymax),
            QgsPointXY(xmax, ymax),
            QgsPointXY(xmax, ymin),
            QgsPointXY(xmin, ymin),
        ]
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPolygonXY([points]))
        provider.addFeatures([feature])
        canvas.refresh()
        return ymax, ymin

    def to_timml(self, other) -> ElementExtraction:
        data = self.table_to_records(layer=self.timml_layer)
        errors = self.schema.validate_timml(
            name=self.timml_layer.name(), data=data, other=other
        )
        if errors:
            return ElementExtraction(errors=errors)
        else:
            x = [point[0] for point in data[0]["geometry"]]
            y = [point[1] for point in data[0]["geometry"]]
            return ElementExtraction(
                data={
                    "xmin": min(x),
                    "xmax": max(x),
                    "ymin": min(y),
                    "ymax": max(y),
                }
            )

    def to_ttim(self, other) -> ElementExtraction:
        timml_extraction = self.to_timml(other)
        data = timml_extraction.data

        timeseries = self.table_to_dict(layer=self.ttim_layer)
        errors = self.schema.validate_timeseries(
            name=self.ttim_layer.name(), data=timeseries
        )
        if errors:
            return ElementExtraction(errors=errors)
        if timeseries["time"]:
            data["time"] = timeseries["time"]
            times = set(timeseries["time"])
        else:
            times = set()
        return ElementExtraction(data=data, times=times)
