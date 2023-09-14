import abc
from collections import defaultdict
from typing import Any, Dict, List

from qgis.core import NULL


def remove_zero_length(geometry):
    # This removes repeated vertices
    return list(dict.fromkeys(geometry))


class ExtractorMixin(abc.ABC):
    @staticmethod
    def argsort(seq):
        return sorted(range(len(seq)), key=seq.__getitem__)

    @staticmethod
    def extract_coordinates(feature):
        geometry = feature.geometry()
        coordinates = []
        for vertex in geometry.vertices():
            coordinates.append((vertex.x(), vertex.y()))
        return coordinates

    @classmethod
    def to_dict(cls, layer) -> List[Dict[str, Any]]:
        features = []
        for feature in layer.getFeatures():
            data = feature.attributeMap()
            for key, value in data.items():
                if value == NULL:
                    data[key] = None
            data["geometry"] = cls.extract_coordinates(feature)
            features.append(data)
        return features

    def table_to_dict(cls, layer) -> Dict[str, Any]:
        features = defaultdict(list)
        for feature in layer.getFeatures():
            features["geometry"].append(cls.extract_coordinates(feature))
            for key, value in feature.attributeMap().items():
                if value == NULL:
                    features[key].append(None)
                else:
                    features[key].append(value)

        # Sort by layer if present.
        # TODO: is this smart? A user may easily miss the layer column.
        # if "layer" in features:
        #    order = cls.argsort(features["layer"])
        #    return {k: [v[i] for i in order] for k, v in features.items()}
        return features

    @staticmethod
    def point_xy(row):
        point = row["geometry"][0]
        return point[0], point[1]

    @staticmethod
    def linestring_xy(row):
        return remove_zero_length(row["geometry"])

    @staticmethod
    def polygon_xy(row):
        return remove_zero_length(row["geometry"])
