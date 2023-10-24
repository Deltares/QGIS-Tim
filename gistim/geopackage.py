"""
Utilities to write data to a geopackage.
"""
import itertools
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, List, NamedTuple, Tuple

import geomet.geopackage
import pandas as pd


class CoordinateReferenceSystem(NamedTuple):
    description: str
    organization: str
    srs_id: int
    wkt: str


class BoundingBox(NamedTuple):
    xmin: float
    ymin: float
    xmax: float
    ymax: float


WGS84_WKT = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]'
APPLICATION_ID = 1196444487
USER_VERSION = 10200


def create_gpkg_contents(
    table_names: List[str], bounding_boxes: List[BoundingBox], srs_id: int
) -> pd.DataFrame:
    # From records?
    return pd.DataFrame(
        data={
            "table_name": table_names,
            "data_type": "features",
            "identifier": table_names,
            "description": "",
            "last_change": pd.Timestamp.now(),
            "min_x": [bb.xmin for bb in bounding_boxes],
            "min_y": [bb.ymin for bb in bounding_boxes],
            "max_x": [bb.xmax for bb in bounding_boxes],
            "max_y": [bb.ymax for bb in bounding_boxes],
            "srs_id": srs_id,
        }
    )


def create_gkpg_spatial_ref_sys(crs: CoordinateReferenceSystem) -> pd.DataFrame:
    return pd.DataFrame(
        data={
            "srs_name": [
                "Undefined Cartesian SRS",
                "Undefined geographic SRS",
                "WGS 84 geodetic",
                crs.description,
            ],
            "srs_id": [-1, 0, 4326, crs.srs_id],
            "organization": ["NONE", "NONE", "EPSG", "EPSG"],
            "organization_coordsys_id": [-1, 0, 4326, crs.organization],
            "definition": ["undefined", "undefined", WGS84_WKT, crs.wkt],
            "description": [
                "undefined Cartesian coordinate reference system",
                "undefined geographic coordinate reference system",
                "longitude/latitude coordinates in decimal degrees on the WGS 84 spheroid",
                "",
            ],
        }
    )


def create_gpkg_geometry_columns(
    table_names: List[str],
    geometry_type_names: List[str],
    srs_id: int,
) -> pd.DataFrame:
    return pd.DataFrame(
        data={
            "table_name": table_names,
            "column_name": "geom",
            "geometry_type_name": geometry_type_names,
            "srs_id": srs_id,
            "z": 0,
            "m": 0,
        }
    )


def collect_bounding_box(features, geometry_type) -> BoundingBox:
    if geometry_type == "Point":
        x = []
        y = []
        for point in features:
            coordinates = point["coordinates"]
            x.append(coordinates[0])
            y.append(coordinates[1])
    else:
        x, y = zip(
            *itertools.chain.from_iterable(line["coordinates"] for line in features)
        )
    return BoundingBox(xmin=min(x), ymin=min(y), xmax=max(x), ymax=max(y))


def process_table(dataframe: pd.DataFrame) -> Tuple[pd.DataFrame, BoundingBox, str]:
    geometry = dataframe.pop("geometry").to_numpy()
    geometry_type = set(f["type"] for f in geometry)
    if len(geometry_type) != 1:
        raise ValueError(
            f"Table should contain exactly one geometry type. Received: {geometry_type}"
        )
    # Get first (and only) member of set.
    geometry_type = next(iter(geometry_type))
    bounding_box = collect_bounding_box(geometry, geometry_type)
    dataframe["geom"] = [geomet.geopackage.dumps(f) for f in geometry]
    return dataframe, bounding_box, geometry_type


def write_geopackage(
    tables: Dict[str, pd.DataFrame], crs: CoordinateReferenceSystem, path: Path
) -> None:
    """
    Write the content of the tables to a geopackage. Overwrites the geopackage
    if it already exists.

    Parameters
    ----------
    tables: Dict[str, pd.DataFrame]
        Mapping of table name to contents, as a dataframe.
        May be an empty dictionary.
    crs: CoordinateReferenceSystem
        Coordinate reference system of the geometries.
    path: Path
        Path to the geopackage to write.

    Returns
    -------
    None
    """
    # We write all tables to a temporary GeoPackage with a dot prefix, and at
    # the end move this over the target file. This does not throw a
    # PermissionError if the file is open in QGIS.
    gpkg_path = path.with_suffix(".output.gpkg")
    temp_path = gpkg_path.with_stem(".")
    # avoid adding tables to existing geopackage.
    temp_path.unlink(missing_ok=True)

    try:
        connection = sqlite3.connect(database=temp_path)
        connection.execute(f"PRAGMA application_id = {APPLICATION_ID};")
        connection.execute(f"PRAGMA user_version = {USER_VERSION};")

        table_names = []
        geometry_types = []
        bounding_boxes = []
        for layername, dataframe in tables.items():
            dataframe, bounding_box, geometry_type = process_table(dataframe)
            table_names.append(layername)
            geometry_types.append(geometry_type)
            bounding_boxes.append(bounding_box)
            dataframe.to_sql(layername, con=connection)

        # Create mandatory geopackage tables.
        gpkg_contents = create_gpkg_contents(
            table_names=table_names, bounding_boxes=bounding_boxes, srs_id=crs.srs_id
        )
        gpkg_geometry_columns = create_gpkg_geometry_columns(
            table_names=table_names,
            geometry_type_names=geometry_types,
            srs_id=crs.srs_id,
        )
        gpkg_spatial_ref_sys = create_gkpg_spatial_ref_sys(crs)
        # Write to Geopackage database.
        gpkg_contents.to_sql(name="gpkg_contents", con=connection)
        gpkg_geometry_columns.to_sql(name="gpkg_geometry_columns", con=connection)
        gpkg_spatial_ref_sys.to_sql(name="gpkg_spatial_ref_sys", con=connection)

    finally:
        connection.commit()
        connection.close()

    shutil.move(temp_path, gpkg_path)
    return
