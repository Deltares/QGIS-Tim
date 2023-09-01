"""
Utilities for processing input or output.

Currently wraps the QGIS functions for turning grids / meshes of head results
into line contours.
"""
import datetime
from typing import NamedTuple

import numpy as np
import processing
from PyQt5.QtCore import QDateTime, QVariant
from qgis.analysis import QgsMeshContours
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsMeshDatasetIndex,
    QgsMeshLayer,
    QgsMeshRendererScalarSettings,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsVectorLayerTemporalProperties,
)


def raster_steady_contours(
    layer: QgsRasterLayer,
    start: float,
    stop: float,
    step: float,
) -> QgsVectorLayer:
    # Seemingly cannot use stop in any way, unless filtering them away.
    result = processing.run(
        "gdal:contour",
        {
            "INPUT": layer,
            "BAND": 1,
            "INTERVAL": step,
            "OFFSET": start,
            "FIELD_NAME": "head",
            "OUTPUT": "TEMPORARY_OUTPUT",
        },
    )

    name = layer.name()
    path = result["OUTPUT"]
    vector_layer = QgsVectorLayer(path)

    result = processing.run(
        "qgis:extractbyexpression",
        {
            "INPUT": vector_layer,
            "EXPRESSION": f'"head" >= {start} AND "head" <= {stop}',
            "OUTPUT": "TEMPORARY_OUTPUT",
        },
    )
    path = result["OUTPUT"]
    return QgsVectorLayer(path, name)


class SteadyContourData(NamedTuple):
    geometry: QgsGeometry
    head: float


class TransientContourData(NamedTuple):
    geometry: QgsGeometry
    head: float
    datetime: datetime.datetime


def steady_contours(
    layer: QgsMeshLayer,
    index: int,
    name: str,
    start: float,
    stop: float,
    step: float,
) -> QgsVectorLayer:
    contourer = QgsMeshContours(layer)

    # Collect contours from mesh layer
    feature_data = []
    qgs_index = QgsMeshDatasetIndex(group=index, dataset=0)
    for value in np.arange(start, stop, step):
        geom = contourer.exportLines(
            qgs_index,
            value,
            QgsMeshRendererScalarSettings.NeighbourAverage,
        )
        if not geom.isNull():
            feature_data.append(SteadyContourData(geom, value))

    # Setup output layer
    contour_layer = QgsVectorLayer("Linestring", f"contours-{name}", "memory")
    contour_layer.setCrs(layer.crs())
    provider = contour_layer.dataProvider()
    provider.addAttributes(
        [
            QgsField("head", QVariant.Double),
        ]
    )
    contour_layer.updateFields()

    # Add items to layer
    for item in feature_data:
        f = QgsFeature()
        f.setGeometry(item.geometry)
        # Make sure to convert to the appropriate Qt types
        # e.g. no numpy floats allowed
        f.setAttributes([float(item.head)])
        provider.addFeature(f)
    contour_layer.updateExtents()

    return contour_layer


def transient_contours(
    layer: QgsMeshLayer,
    index: int,
    name: str,
    start: float,
    stop: float,
    step: float,
) -> QgsVectorLayer:
    first_index = QgsMeshDatasetIndex(group=index, dataset=0)
    ntime = layer.datasetCount(first_index)
    ref_time = layer.datasetGroupMetadata(first_index).referenceTime().toPyDateTime()
    contourer = QgsMeshContours(layer)

    # Setup output layer
    contour_layer = QgsVectorLayer("Linestring", f"contours-{name}", "memory")
    contour_layer.setCrs(layer.crs())
    provider = contour_layer.dataProvider()
    provider.addAttributes(
        [
            QgsField("head", QVariant.Double),
            QgsField("datetime_start", QVariant.DateTime),
            QgsField("datetime_end", QVariant.DateTime),
        ]
    )
    contour_layer.updateFields()

    # Collect contours from mesh layer
    feature_data = []
    for time_index in range(ntime):
        qgs_index = QgsMeshDatasetIndex(group=index, dataset=time_index)
        for value in np.arange(start, stop, step):
            geom = contourer.exportLines(
                qgs_index,
                value,
                QgsMeshRendererScalarSettings.NeighbourAverage,
            )
            if not geom.isNull():
                mdal_time = layer.datasetMetadata(
                    QgsMeshDatasetIndex(index, time_index)
                ).time()
                date = ref_time + datetime.timedelta(hours=mdal_time)
                feature_data.append(TransientContourData(geom, value, date))

    if len(feature_data) == 0:
        return contour_layer

    # Create a dictionary to find the end date to accompany every
    # starting date
    dates = sorted(list(set(item.datetime for item in feature_data)))
    end_dates = {
        a: b - datetime.timedelta(minutes=1) for a, b in zip(dates[:-1], dates[1:])
    }
    end_dates[dates[-1]] = dates[-1] + datetime.timedelta(days=1)

    # Add items to layer
    for item in feature_data:
        f = QgsFeature()
        f.setGeometry(item.geometry)
        # Make sure to convert to the appropriate Qt types
        # e.g. no numpy floats allowed
        f.setAttributes(
            [
                float(item.head),
                QDateTime(item.datetime),
                QDateTime(end_dates[item.datetime]),
            ]
        )
        provider.addFeature(f)
    contour_layer.updateExtents()

    # Set the temporal properties
    temporal_properties = contour_layer.temporalProperties()
    temporal_properties.setStartField("datetime_start")
    temporal_properties.setEndField("datetime_end")
    temporal_properties.setMode(
        QgsVectorLayerTemporalProperties.ModeFeatureDateTimeStartAndEndFromFields
    )
    temporal_properties.setIsActive(True)

    return contour_layer


def mesh_contours(
    layer: QgsMeshLayer,
    index: int,
    name: str,
    start: float,
    stop: float,
    step: float,
) -> QgsVectorLayer:
    if layer.firstValidTimeStep().isValid():
        return transient_contours(layer, index, name, start, stop, step)
    else:
        return steady_contours(layer, index, name, start, stop, step)
