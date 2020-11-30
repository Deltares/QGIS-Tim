"""
This module deals with resolving intersections between vector elements.

Within analytic element modeling, lines or edges cannot intersect each other.
Instead, an explicit intersection point is required. In terms of geometric
operations, this requires "inserting" the intersection points for every
intersecting geometry.

This module will automatically find, and insert intersection points.

                   Linestring 1
                   | 
                   |
Linestring 2 -- -- + -- --
                   |
                   |

TODO: Polygon inhomogeneties may intersect each other as well; they should only
touch each other. Easiest way to include this is likely with an ordinal column
to determine precedence ("cellsize" so far, will be changed to "precedence?").
"""
import functools
import operator
from typing import Any, Optional, Sequence, Tuple

import geopandas as gpd
import numpy as np
import shapely
import shapely.geometry as sg

FloatArray = np.ndarray
IntArray = np.ndarray


def flatten(seq: Sequence[Any]) -> Sequence[Any]:
    """
    Flatten nested sequences into a single, flat, sequence.
    """
    return functools.reduce(operator.concat, seq)


def separate(
    gdf: gpd.GeoDataFrame,
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    polygons = gdf[[isinstance(x, sg.Polygon) for x in gdf["geometry"]]]
    linestrings = gdf[[isinstance(x, sg.LineString) for x in gdf["geometry"]]]
    points = gdf[[isinstance(x, sg.Point) for x in gdf["geometry"]]]
    # Set crs to None to avoid crs warnings on joins and overlays
    polygons.crs = linestrings.crs = points.crs = None
    return polygons, linestrings, points


def resolve_polygons(
    gdf_poly: gpd.GeoDataFrame,
    gdf_line: gpd.GeoDataFrame,
    dissolve: bool = False,
) -> gpd.GeoDataFrame:
    # Collect the original interiors, first create a flat list
    inner_rings = gpd.GeoSeries(flatten(gdf_poly.interiors))
    interiors = gpd.GeoDataFrame(geometry=[sg.asPolygon(ring) for ring in inner_rings])
    buffer_interiors = interiors.copy()
    buffer_interiors.geometry = buffer_interiors.buffer(1.0e-6)
    negbuffer_interiors = interiors.copy()
    negbuffer_interiors.geometry = negbuffer_interiors.buffer(-1.0e-6)
    rings = gdf_poly.exterior.append(inner_rings)
    if len(gdf_line) > 0:
        rings.append(gpd.GeoSeries(gdf_line.unary_union))

    # Exterior produces a linear ring of the exteriors. Feeding linear rings
    # into unary_union cuts the lines at every intersection. Polygonize turns
    # the intersected parts into new polygons.
    polygons = [polygon for polygon in shapely.ops.polygonize(rings.unary_union)]
    tmp = gpd.GeoDataFrame(geometry=polygons)
    # Remove interior polygons, but not those fully within ("islands")
    not_interior = gpd.sjoin(tmp, buffer_interiors, how="left", op="within")[
        "index_right"
    ].isnull()
    is_island = gpd.sjoin(tmp, negbuffer_interiors, how="left", op="within")[
        "index_right"
    ].notnull()
    not_interior = not_interior.groupby(not_interior.index).any()
    is_island = is_island.groupby(is_island.index).any()
    not_a_hole = not_interior.values | is_island.values
    hole_points = tmp[~not_a_hole].representative_point()
    tmp = tmp[not_a_hole]

    # By utilizing the exterior and the unary_union, we've lost the attributes.
    # We'll put them back in place using a spatial join. Note that the smallest
    # cellsize should have precedence. We resolve this by sorting so that the
    # smallest cellsizes come last, and then dropping the duplicate values (of
    # the index), thereby keeping the smallest cellsizes.
    gdf_poly = gdf_poly.sort_values(by="cellsize", ascending=False)
    gdf_poly.geometry = gdf_poly.buffer(1.0e-6)
    tmp = gpd.sjoin(tmp, gdf_poly, how="left", op="within")

    # From the intersection, we've created the necessary hanging nodes. However,
    # we're not interested in edges between those hanging nodes, so we dissolve
    # those; dissolve also groups non-adjacent polygons into multi-polygons, we
    # get rid of those with explode.
    if dissolve:
        tmp = tmp[~tmp.index.duplicated(keep="last")].dissolve(by="cellsize").explode()
        out = gpd.GeoDataFrame(
            {
                "__polygon_id": np.arange(1, len(tmp) + 1),
                "cellsize": tmp.index.get_level_values("cellsize"),
                "geometry": tmp["geometry"].values,
            }
        )
    # This isn't necessary for e.g. Triangle meshing; it can deal with segments
    # touching each other. However, this means a linestring can cut a polygon in
    # half. In that case, we need a region point in every part of the split polygon.
    else:
        out = gpd.GeoDataFrame(
            {
                "__polygon_id": np.arange(1, len(tmp) + 1),
                "cellsize": tmp["cellsize"].values,
                "geometry": tmp["geometry"].values,
            }
        )
    return out, hole_points


def resolve_features(gdf: gpd.GeoDataFrame, polygons: gpd.GeoDataFrame):
    out = gpd.overlay(gdf, polygons, how="intersection").explode()["geometry"]
    out.index = np.arange(1, len(out) + 1)
    return out


def resolve_geometry(gdf: gpd.GeoDataFrame):
    polygons, linestrings, points = separate(gdf)
    polygons, hole_points = resolve_polygons(polygons, linestrings, dissolve=False)
    if len(linestrings) > 0:
        linestrings = resolve_features(linestrings, polygons)
    if len(points) > 0:
        points = resolve_features(points, polygons)

    return polygons, linestrings, points, hole_points
