from typing import Union

import numpy as np
import xarray as xr

FloatArray = np.ndarray
IntArray = np.ndarray


def _check_monotonic(dxs, dim):
    # use xor to check if one or the other
    if not ((dxs > 0.0).all() ^ (dxs < 0.0).all()):
        raise ValueError(f"{dim} is not only increasing or only decreasing")


def _coord(da, dim):
    """
    Transform N xarray midpoints into N + 1 vertex edges
    """
    delta_dim = "d" + dim  # e.g. dx, dy, dz, etc.

    # If empty array, return empty
    if da[dim].size == 0:
        return np.array(())

    if delta_dim in da.coords:  # equidistant or non-equidistant
        dx = da[delta_dim].values
        if dx.shape == () or dx.shape == (1,):  # scalar -> equidistant
            dxs = np.full(da[dim].size, dx)
        else:  # array -> non-equidistant
            dxs = dx
        _check_monotonic(dxs, dim)

    else:  # undefined -> equidistant
        if da[dim].size == 1:
            raise ValueError(
                f"DataArray has size 1 along {dim}, so cellsize must be provided"
                " as a coordinate."
            )
        dxs = np.diff(da[dim].values)
        dx = dxs[0]
        atolx = abs(1.0e-4 * dx)
        if not np.allclose(dxs, dx, atolx):
            raise ValueError(
                f"DataArray has to be equidistant along {dim}, or cellsizes"
                " must be provided as a coordinate."
            )
        dxs = np.full(da[dim].size, dx)

    dxs = np.abs(dxs)
    x = da[dim].values
    if not da.indexes[dim].is_monotonic_increasing:
        x = x[::-1]
        dxs = dxs[::-1]

    # This assumes the coordinate to be monotonic increasing
    x0 = x[0] - 0.5 * dxs[0]
    x = np.full(dxs.size + 1, x0)
    x[1:] += np.cumsum(dxs)
    return x


def _ugrid2d_dataset(
    node_x: FloatArray,
    node_y: FloatArray,
    face_x: FloatArray,
    face_y: FloatArray,
    face_nodes: IntArray,
) -> xr.Dataset:
    ds = xr.Dataset()
    ds["mesh2d"] = xr.DataArray(
        data=0,
        attrs={
            "cf_role": "mesh_topology",
            "long_name": "Topology data of 2D mesh",
            "topology_dimension": 2,
            "node_coordinates": "node_x node_y",
            "face_node_connectivity": "face_nodes",
            "edge_node_connectivity": "edge_nodes",
        },
    )
    ds = ds.assign_coords(
        node_x=xr.DataArray(
            data=node_x,
            dims=["node"],
        )
    )
    ds = ds.assign_coords(
        node_y=xr.DataArray(
            data=node_y,
            dims=["node"],
        )
    )
    ds["face_nodes"] = xr.DataArray(
        data=face_nodes,
        coords={
            "face_x": ("face", face_x),
            "face_y": ("face", face_y),
        },
        dims=["face", "nmax_face"],
        attrs={
            "cf_role": "face_node_connectivity",
            "long_name": "Vertex nodes of mesh faces (counterclockwise)",
            "start_index": 0,
            "_FillValue": -1,
        },
    )
    ds.attrs = {"Conventions": "CF-1.8 UGRID-1.0"}
    return ds


def ugrid2d_topology(data: Union[xr.DataArray, xr.Dataset]) -> xr.Dataset:
    """
    Derive the 2D-UGRID quadrilateral mesh topology from a structured DataArray
    or Dataset, with (2D-dimensions) "y" and "x".

    Parameters
    ----------
    data: Union[xr.DataArray, xr.Dataset]
        Structured data from which the "x" and "y" coordinate will be used to
        define the UGRID-2D topology.

    Returns
    -------
    ugrid_topology: xr.Dataset
        Dataset with the required arrays describing 2D unstructured topology:
        node_x, node_y, face_x, face_y, face_nodes (connectivity).
    """
    # Transform midpoints into vertices
    # These are always returned monotonically increasing
    x = data["x"].values
    xcoord = _coord(data, "x")
    if not data.indexes["x"].is_monotonic_increasing:
        xcoord = xcoord[::-1]
    y = data["y"].values
    ycoord = _coord(data, "y")
    if not data.indexes["y"].is_monotonic_increasing:
        ycoord = ycoord[::-1]
    # Compute all vertices, these are the ugrid nodes
    node_y, node_x = (a.ravel() for a in np.meshgrid(ycoord, xcoord, indexing="ij"))
    face_y, face_x = (a.ravel() for a in np.meshgrid(y, x, indexing="ij"))
    linear_index = np.arange(node_x.size, dtype=np.int).reshape(
        ycoord.size, xcoord.size
    )
    # Allocate face_node_connectivity
    nfaces = (ycoord.size - 1) * (xcoord.size - 1)
    face_nodes = np.empty((nfaces, 4))
    # Set connectivity in counterclockwise manner
    face_nodes[:, 0] = linear_index[:-1, 1:].ravel()  # upper right
    face_nodes[:, 1] = linear_index[:-1, :-1].ravel()  # upper left
    face_nodes[:, 2] = linear_index[1:, :-1].ravel()  # lower left
    face_nodes[:, 3] = linear_index[1:, 1:].ravel()  # lower right
    # Tie it together
    ds = _ugrid2d_dataset(node_x, node_y, face_x, face_y, face_nodes)
    return ds


def ugrid2d_data(da: xr.DataArray) -> xr.DataArray:
    """
    Reshape a structured (x, y) DataArray into unstructured (face) form.
    Extra dimensions are maintained:
    e.g. (time, layer, x, y) becomes (time, layer, face).

    Parameters
    ----------
    da: xr.DataArray
        Structured DataArray with last two dimensions ("y", "x").

    Returns
    -------
    Unstructured DataArray with dimensions ("y", "x") replaced by ("face",).
    """
    if da.dims[:-2] == ("y", "x"):
        raise ValueError('Last two dimensions must be ("y", "x").')
    extra_dims = list(set(da.dims) - set(["y", "x"]))
    shape = da.data.shape
    new_shape = shape[:-2] + (np.product(shape[-2:]),)
    return xr.DataArray(
        data=da.data.reshape(new_shape),
        coords={k: da[k] for k in da.coords if k not in ("y", "x", "dy", "dx")},
        dims=extra_dims + ["face"],
    )


def _unstack_layers(ds: xr.Dataset) -> xr.Dataset:
    """
    Unstack the layer dimensions, as MDAL does not have support for
    UGRID-2D-layered datasets yet. Layers are stored as separate variables
    instead for now.
    """
    for variable in ds.data_vars:
        if "layer" in ds[variable].dims:
            stacked = ds[variable]
            ds = ds.drop_vars(variable)
            for layer in stacked["layer"].values:
                ds[f"{variable}_layer_{layer}"] = stacked.sel(layer=layer)
    if "layer" in ds.dims:
        ds = ds.drop("layer")
    return ds


def to_ugrid2d(data: Union[xr.DataArray, xr.Dataset]) -> xr.Dataset:
    """
    Convert a structured DataArray or Dataset into its UGRID-2D quadrilateral
    equivalent.

    See:
    https://ugrid-conventions.github.io/ugrid-conventions/#2d-flexible-mesh-mixed-triangles-quadrilaterals-etc-topology

    Parameters
    ----------
    data: Union[xr.DataArray, xr.Dataset]
        Dataset or DataArray with last two dimensions ("y", "x").
        In case of a Dataset, the 2D topology is defined once and variables are
        added one by one.
        In case of a DataArray, a name is required; a name can be set with:
        ``da.name = "..."``'

    Returns
    -------
    ugrid2d_dataset: xr.Dataset
        The equivalent data, in UGRID-2D quadrilateral form.
    """
    ds = ugrid2d_topology(data)
    if isinstance(data, xr.DataArray):
        if data.name is None:
            raise ValueError(
                'A name is required for the DataArray. It can be set with ``da.name = "..."`'
            )
        ds[data.name] = ugrid2d_data(data)
    elif isinstance(data, xr.Dataset):
        for variable in data.data_vars:
            ds[variable] = ugrid2d_data(data[variable])
    else:
        raise TypeError("data must be xarray.DataArray or xr.Dataset")
    # MDAL expects dates encoded as float, not integer, which is what xarray defaults to.
    # This leads to the variables not even showing up.
    for dim in ds.dims:
        if np.issubdtype(ds[dim].dtype, np.datetime64):
            ds[dim].encoding["dtype"] = float
    return _unstack_layers(ds)
