from typing import List

from qgis.core import (
    QgsColorRampShader,
    QgsFillSymbol,
    QgsRasterBandStats,
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer,
    QgsSingleSymbolRenderer,
    QgsStyle,
)


def color_ramp_items(
    colormap: str, minimum: float, maximum: float, nclass: int
) -> List[QgsColorRampShader.ColorRampItem]:
    delta = maximum - minimum
    fractional_steps = [i / nclass for i in range(nclass + 1)]
    ramp = QgsStyle().defaultStyle().colorRamp(colormap)
    colors = [ramp.color(f) for f in fractional_steps]
    steps = [minimum + f * delta for f in fractional_steps]
    return [
        QgsColorRampShader.ColorRampItem(step, color, str(step))
        for step, color in zip(steps, colors)
    ]


def pseudocolor_renderer(
    layer, band: int, colormap: str, nclass: int
) -> QgsSingleBandPseudoColorRenderer:
    stats = layer.dataProvider().bandStatistics(band, QgsRasterBandStats.All)
    minimum = stats.minimumValue
    maximum = stats.maximumValue

    ramp_items = color_ramp_items(colormap, minimum, maximum, nclass)
    shader_function = QgsColorRampShader()
    shader_function.setClassificationMode(QgsColorRampShader.EqualInterval)
    shader_function.setColorRampItemList(ramp_items)

    raster_shader = QgsRasterShader()
    raster_shader.setRasterShaderFunction(shader_function)

    return QgsSingleBandPseudoColorRenderer(layer.dataProvider(), band, raster_shader)


def domain_renderer() -> QgsSingleSymbolRenderer:
    symbol = QgsFillSymbol.createSimple(
        {
            "color": "255,0,0,0",  # transparent
            "color_border": "#000000#",  # black
            "width_border": "0.5",
        }
    )
    return QgsSingleSymbolRenderer(symbol)


def circareasink_renderer() -> QgsSingleSymbolRenderer:
    symbol = QgsFillSymbol.createSimple(
        {
            "color": "255,0,0,0",  # transparent
            "color_border": "#3182bd",  # blue
            "width_border": "0.75",
        }
    )
    return QgsSingleSymbolRenderer(symbol)
