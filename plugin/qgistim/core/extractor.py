import abc
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from qgis.core import NULL


def remove_zero_length(geometry):
    # This removes repeated vertices
    return list(dict.fromkeys(geometry))


class ExtractorMixin(abc.ABC):
    """
    Mixin class to extract all data from QgsVectorLayers.
    """

    @staticmethod
    def argsort(seq):
        return sorted(range(len(seq)), key=seq.__getitem__)

    @staticmethod
    def extract_coordinates(feature):
        geometry = feature.geometry()
        coordinates = []
        for vertex in geometry.vertices():
            coordinates.append((vertex.x(), vertex.y()))
        centroid = geometry.centroid().asPoint()
        return (centroid.x(), centroid.y()), coordinates

    @classmethod
    def table_to_records(cls, layer) -> List[Dict[str, Any]]:
        features = []
        for feature in layer.getFeatures():
            data = feature.attributeMap()
            for key, value in data.items():
                if value == NULL:
                    data[key] = None
            geomtype = layer.geometryType()
            # Skip if no geometry is present.
            if geomtype != geomtype.Null:
                data["centroid"], data["geometry"] = cls.extract_coordinates(feature)
            features.append(data)
        return features

    def table_to_dict(cls, layer) -> Dict[str, Any]:
        features = defaultdict(list)
        for feature in layer.getFeatures():
            for key, value in feature.attributeMap().items():
                if value == NULL:
                    features[key].append(None)
                else:
                    features[key].append(value)
        return features

    @staticmethod
    def point_xy(row) -> Tuple[List[float], List[float]]:
        point = row["geometry"][0]
        return point[0], point[1]

    @staticmethod
    def linestring_xy(row) -> List:
        return remove_zero_length(row["geometry"])

    @staticmethod
    def polygon_xy(row) -> List:
        return remove_zero_length(row["geometry"])
