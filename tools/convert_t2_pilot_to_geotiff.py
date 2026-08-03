"""Convert the approved February 2020 pilot NetCDF to two-band GeoTIFFs.

This tool is intentionally offline-only. It reads one user-provided NetCDF,
decodes CF packing once through xarray, preserves NaN as nodata, performs no
resampling, and writes one float32 GeoTIFF per daily timestep with bands
``uo`` and ``vo``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import rioxarray  # noqa: F401  # registers the .rio accessor
import xarray as xr


EXPECTED_VARIABLES = ("uo", "vo")
EXPECTED_UNIT = "m s-1"
EXPECTED_START = "2020-02-01"
EXPECTED_END = "2020-02-29"
EXPECTED_TIMESTEPS = 29
EXPECTED_DEPTH_M = 0.494025
DEPTH_TOLERANCE_M = 1e-6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, dest="input_path")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="glorys12v1_daily_surface")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"ERROR: {message}")


def validate_dataset(ds: xr.Dataset) -> None:
    missing = [name for name in EXPECTED_VARIABLES if name not in ds.data_vars]
    if missing:
        fail(f"missing required variables: {','.join(missing)}")
    for name in EXPECTED_VARIABLES:
        if ds[name].attrs.get("units") != EXPECTED_UNIT:
            fail(f"{name} units are not {EXPECTED_UNIT!r}")

    required_dims = {"time", "depth", "latitude", "longitude"}
    missing_dims = required_dims.difference(ds.dims)
    if missing_dims:
        fail(f"missing required dimensions: {','.join(sorted(missing_dims))}")
    if ds.sizes["time"] != EXPECTED_TIMESTEPS:
        fail(f"expected {EXPECTED_TIMESTEPS} timesteps, found {ds.sizes['time']}")
    expected_times = pd.date_range(
        EXPECTED_START, EXPECTED_END, freq="D", inclusive="both"
    )
    actual_times = pd.DatetimeIndex(ds.time.values)
    if not actual_times.equals(expected_times):
        fail("time coordinate is not the exact February 2020 pilot sequence")

    if ds.sizes["depth"] != 1:
        fail(f"expected one selected depth, found {ds.sizes['depth']}")
    depth_value = float(ds.depth.values[0])
    if abs(depth_value - EXPECTED_DEPTH_M) > DEPTH_TOLERANCE_M:
        fail(f"depth {depth_value} is outside the approved tolerance")

    for coordinate in ("latitude", "longitude"):
        values = np.asarray(ds[coordinate].values)
        if values.ndim != 1 or values.size < 2:
            fail(f"{coordinate} must be a one-dimensional coordinate")
        if not np.all(np.diff(values) > 0) and not np.all(np.diff(values) < 0):
            fail(f"{coordinate} must be strictly monotonic")


def convert(input_path: Path, output_dir: Path, prefix: str, overwrite: bool) -> dict:
    if not input_path.is_file():
        fail(f"input file does not exist: {input_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    with xr.open_dataset(
        input_path, engine="h5netcdf", decode_cf=True, mask_and_scale=True
    ) as source:
        validate_dataset(source)
        selected = source[list(EXPECTED_VARIABLES)].isel(depth=0)
        selected = selected.transpose("time", "latitude", "longitude")
        if float(selected.latitude.values[0]) < float(selected.latitude.values[-1]):
            # GeoTIFF rows run north to south. This reverses row order only;
            # it does not resample or change the source grid.
            selected = selected.sortby("latitude", ascending=False)

        outputs: list[str] = []
        for index, timestamp in enumerate(pd.DatetimeIndex(selected.time.values)):
            stamp = timestamp.strftime("%Y%m%d")
            output_path = output_dir / f"{prefix}_{stamp}.tif"
            if output_path.exists() and not overwrite:
                fail(f"output exists; pass --overwrite to replace: {output_path}")
            frame = selected.isel(time=index).to_array(dim="band").astype("float32")
            frame = frame.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude")
            frame = frame.rio.write_crs("EPSG:4326")
            frame = frame.rio.write_nodata(np.nan)
            frame.rio.to_raster(
                output_path,
                driver="GTiff",
                dtype="float32",
                nodata=np.nan,
                compress="deflate",
                predictor=3,
            )
            with rasterio.open(output_path, "r+") as raster:
                raster.set_band_description(1, "uo")
                raster.set_band_description(2, "vo")
                raster.update_tags(
                    source_file=input_path.name,
                    time=timestamp.isoformat(),
                    depth_m=str(float(source.depth.values[0])),
                    variables="uo,vo",
                    units=EXPECTED_UNIT,
                    resampling="none",
                )
            outputs.append(str(output_path))

        summary = {
            "status": "PASS_WITH_NOTES",
            "input": str(input_path),
            "output_count": len(outputs),
            "outputs": outputs,
            "bands": list(EXPECTED_VARIABLES),
            "units": EXPECTED_UNIT,
            "depth_m": float(source.depth.values[0]),
            "crs": "EPSG:4326",
            "nodata": "NaN",
            "resampling": "none",
            "limitations": [
                "No Earth Engine upload or computation was performed.",
                "Exact polygon/water mask remains downstream.",
            ],
        }
    return summary


def main() -> int:
    args = parse_args()
    summary = convert(args.input_path, args.output_dir, args.prefix, args.overwrite)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
