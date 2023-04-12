"""
Some layer styling for output.

We'd like contours to look the same consistently. A Domain should be
transparent, not obscuring the view. A head grid should have pseudocoloring,
ideally with a legend stretching from minimum to maximum.
"""
from typing import List

from PyQt5.QtGui import QColor
from qgis.core import (
    QgsColorRampShader,
    QgsLineSymbol,
    QgsPalLayerSettings,
    QgsRasterBandStats,
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer,
    QgsSingleSymbolRenderer,
    QgsStyle,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayerSimpleLabeling,
)


def color_ramp_items(
    colormap: str, minimum: float, maximum: float, nclass: int
) -> List[QgsColorRampShader.ColorRampItem]:
    """
    Parameters
    ----------
    colormap: str
        Name of QGIS colormap
    minimum: float
    maximum: float
    nclass: int
        Number of colormap classes to create

    Returns
    -------
    color_ramp_items: List[QgsColorRampShader.ColorRampItem]
        Can be used directly by the QgsColorRampShader
    """
    delta = maximum - minimum
    fractional_steps = [i / nclass for i in range(nclass + 1)]
    ramp = QgsStyle().defaultStyle().colorRamp(colormap)
    colors = [ramp.color(f) for f in fractional_steps]
    steps = [minimum + f * delta for f in fractional_steps]
    return ramp, [
        QgsColorRampShader.ColorRampItem(step, color, str(step))
        for step, color in zip(steps, colors)
    ]


def pseudocolor_renderer(
    layer, band: int, colormap: str, nclass: int
) -> QgsSingleBandPseudoColorRenderer:
    """
    Parameters
    ----------
    layer: QGIS map layer
    band: int
        band number of the raster to create a renderer for
    colormap: str
        Name of QGIS colormap
    nclass: int
        Number of colormap classes to create

    Returns
    -------
    renderer: QgsSingleBandPseudoColorRenderer
    """
    stats = layer.dataProvider().bandStatistics(band, QgsRasterBandStats.All)
    minimum = stats.minimumValue
    maximum = stats.maximumValue

    ramp, ramp_items = color_ramp_items(colormap, minimum, maximum, nclass)
    shader_function = QgsColorRampShader()
    shader_function.setMinimumValue(minimum)
    shader_function.setMaximumValue(maximum)
    shader_function.setSourceColorRamp(ramp)
    shader_function.setColorRampType(QgsColorRampShader.Interpolated)
    shader_function.setClassificationMode(QgsColorRampShader.EqualInterval)
    shader_function.setColorRampItemList(ramp_items)

    raster_shader = QgsRasterShader()
    raster_shader.setRasterShaderFunction(shader_function)

    return QgsSingleBandPseudoColorRenderer(layer.dataProvider(), band, raster_shader)


def contour_renderer() -> QgsSingleSymbolRenderer:
    symbol = QgsLineSymbol.createSimple(
        {
            "color": "#000000#",  # black
            "width": "0.25",
        }
    )
    return QgsSingleSymbolRenderer(symbol)


def number_labels(field: str) -> QgsVectorLayerSimpleLabeling:
    pal_layer = QgsPalLayerSettings()
    pal_layer.fieldName = field
    pal_layer.enabled = True
    pal_layer.placement = QgsPalLayerSettings.Line
    pal_layer.formatNumbers = True
    pal_layer.decimals = 2

    buffer_settings = QgsTextBufferSettings()
    buffer_settings.setEnabled(True)
    buffer_settings.setSize(1)
    buffer_settings.setColor(QColor("white"))

    text_format = QgsTextFormat()
    text_format.setBuffer(buffer_settings)

    pal_layer.setFormat(text_format)
    labels = QgsVectorLayerSimpleLabeling(pal_layer)
    return labels
