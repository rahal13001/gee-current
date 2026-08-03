"""Validate pilot GeoTIFFs against the CF-decoded source NetCDF."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import xarray as xr


VARIABLES = ("uo", "vo")
EXPECTED_DATES = pd.date_range("2020-02-01", "2020-02-29", freq="D")
ABSOLUTE_TOLERANCE = 1e-6
NODATA_VALUE = -9999.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--netcdf", type=Path, required=True)
    parser.add_argument("--geotiff-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="glorys12v1_daily_surface")
    return parser.parse_args()


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"ERROR: {message}")


def main() -> int:
    args = parse_args()
    if not args.netcdf.is_file():
        fail(f"NetCDF does not exist: {args.netcdf}")
    if not args.geotiff_dir.is_dir():
        fail(f"GeoTIFF directory does not exist: {args.geotiff_dir}")

    checked: list[str] = []
    max_abs_difference = 0.0
    with xr.open_dataset(
        args.netcdf, engine="h5netcdf", decode_cf=True, mask_and_scale=True
    ) as source:
        selected = source[list(VARIABLES)].isel(depth=0).transpose(
            "time", "latitude", "longitude"
        )
        if float(selected.latitude.values[0]) < float(selected.latitude.values[-1]):
            selected = selected.sortby("latitude", ascending=False)
        actual_times = pd.DatetimeIndex(selected.time.values)
        if not actual_times.equals(EXPECTED_DATES):
            fail("NetCDF does not contain the exact 29-day pilot sequence")

        for index, timestamp in enumerate(EXPECTED_DATES):
            stamp = timestamp.strftime("%Y%m%d")
            path = args.geotiff_dir / f"{args.prefix}_{stamp}.tif"
            if not path.is_file():
                fail(f"missing GeoTIFF: {path}")
            with rasterio.open(path) as raster:
                if raster.count != 2:
                    fail(f"{path.name}: expected two bands, found {raster.count}")
                if raster.dtypes != ("float32", "float32"):
                    fail(f"{path.name}: expected float32 bands, found {raster.dtypes}")
                if raster.crs is None or raster.crs.to_epsg() != 4326:
                    fail(f"{path.name}: CRS is not EPSG:4326")
                if tuple(raster.descriptions) != VARIABLES:
                    fail(f"{path.name}: band descriptions are not uo/vo")
                if raster.nodata != NODATA_VALUE:
                    fail(f"{path.name}: nodata is not {NODATA_VALUE}")
                if raster.tags().get("time", "") != timestamp.isoformat():
                    fail(f"{path.name}: time tag mismatch")
                actual = raster.read(masked=True).filled(np.nan).astype(np.float64)
                expected = np.stack(
                    [selected[name].isel(time=index).values for name in VARIABLES]
                )
                if actual.shape != expected.shape:
                    fail(f"{path.name}: shape mismatch {actual.shape} != {expected.shape}")
                if not np.array_equal(np.isnan(actual), np.isnan(expected)):
                    fail(f"{path.name}: NaN mask mismatch")
                valid = np.isfinite(expected)
                if valid.any():
                    difference = np.abs(actual[valid] - expected[valid])
                    file_max = float(difference.max())
                    max_abs_difference = max(max_abs_difference, file_max)
                    if file_max > ABSOLUTE_TOLERANCE:
                        fail(
                            f"{path.name}: max absolute difference {file_max} exceeds "
                            f"{ABSOLUTE_TOLERANCE}"
                        )
            checked.append(str(path))

    print(
        json.dumps(
            {
                "status": "PASS_WITH_NOTES",
                "file_count": len(checked),
                "band_count": 2,
                "bands": list(VARIABLES),
                "crs": "EPSG:4326",
                "nodata": NODATA_VALUE,
                "absolute_tolerance": ABSOLUTE_TOLERANCE,
                "max_absolute_difference": max_abs_difference,
                "resampling": "none",
                "limitations": [
                    "No Earth Engine upload or computation was performed.",
                    "Exact polygon/water mask remains downstream.",
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
