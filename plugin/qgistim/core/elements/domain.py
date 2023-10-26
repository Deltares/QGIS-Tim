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
from qgistim.core.elements.element import ElementSchema, TransientElement
from qgistim.core.schemata import AllRequired, Positive, Required, SingleRow


class DomainSchema(ElementSchema):
    timml_schemata = {"geometry": Required()}
    timml_consistency_schemata = (SingleRow(),)
    timeseries_schemata = {
        "time": AllRequired(Positive()),
    }


class Domain(TransientElement):
    element_type = "Domain"
    geometry_type = "Polygon"
    ttim_attributes = (QgsField("time", QVariant.Double),)
    schema = DomainSchema()

    def __init__(self, path: str, name: str):
        self.times = []
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

    def to_timml(self, other):
        data = self.table_to_records(self.timml_layer)
        errors = self.schema.validate_timml(data, other)
        if errors:
            return errors, None
        else:
            x = [point[0] for point in data[0]["geometry"]]
            y = [point[1] for point in data[0]["geometry"]]
            return None, {
                "xmin": min(x),
                "xmax": max(x),
                "ymin": min(y),
                "ymax": max(y),
            }

    def to_ttim(self, other):
        _, data = self.to_timml(other)
        ttim_data = self.table_to_dict(self.ttim_layer)
        ttim_errors = self.schema.validate_ttim(ttim_data, other)
        data["time"] = ttim_data["time"]
        self.times = [max(data["time"])]
        return ttim_errors, data
