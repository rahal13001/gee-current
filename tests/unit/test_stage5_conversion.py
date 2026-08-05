from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import rasterio
import xarray as xr

from python.checksum import sha256_file
from python.conversion import (
    ConversionError,
    audit_collection_outputs,
    compare_collection_outputs,
    compare_job_outputs,
    config_hash,
    convert_collection,
    convert_job,
)


class Stage5ConversionTests(unittest.TestCase):
    def _fixture(
        self,
        folder: Path,
        *,
        latitude: tuple[float, ...] = (-1.0, 0.0),
        longitude: tuple[float, ...] = (130.0, 131.0, 132.0),
        mask_mismatch: bool = False,
        irregular_longitude: bool = False,
    ) -> tuple[Path, dict[str, object], Path]:
        times = np.array(["2020-02-01", "2020-02-02"], dtype="datetime64[ns]")
        latitudes = np.array(latitude, dtype="float32")
        longitudes = np.array(longitude, dtype="float32")
        if irregular_longitude:
            longitudes = np.array((130.0, 131.2, 132.0), dtype="float32")
        shape = (len(times), 1, len(latitudes), len(longitudes))
        uo = np.arange(np.prod(shape), dtype="float32").reshape(shape) / 100.0
        vo = uo + 1.0
        uo[:, :, -1, -1] = np.nan
        vo[:, :, -1, -1] = np.nan
        if mask_mismatch:
            vo[:, :, 0, 0] = np.nan
        dataset = xr.Dataset(
            {
                "uo": (("time", "depth", "latitude", "longitude"), uo, {"units": "m s-1"}),
                "vo": (("time", "depth", "latitude", "longitude"), vo, {"units": "m s-1"}),
            },
            coords={
                "time": times,
                "depth": np.array([0.494025], dtype="float32"),
                "latitude": latitudes,
                "longitude": longitudes,
            },
        )
        source = folder / "fixture.nc"
        dataset.to_netcdf(source, engine="h5netcdf")
        config = folder / "config.json"
        config.write_text('{"fixture": true}\n', encoding="utf-8")
        entry: dict[str, object] = {
            "job_id": "daily_jfm_2020_02",
            "plan_name": "daily_jfm",
            "relative_path": "fixture.nc",
            "source_checksum": sha256_file(source),
            "status": "PASS",
            "expected_timesteps": 2,
            "start_datetime": "2020-02-01T00:00:00",
            "end_datetime": "2020-02-02T23:59:59",
            "dataset_id": "fixture-dataset",
            "dataset_version": "fixture-version",
            "dataset_part": "fixture-part",
        }
        return source, entry, config

    def test_conversion_preserves_mask_zero_band_order_and_orientation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source, entry, config = self._fixture(folder)
            output_dir = folder / "tiffs"
            report = convert_job(
                root=folder,
                entry=entry,
                output_dir=output_dir,
                config_hash_value=config_hash([config], root=folder),
                prefix="fixture",
            )
            self.assertEqual(report["output_count"], 2)
            first = output_dir / "fixture_20200201T000000.tif"
            with rasterio.open(first) as raster:
                self.assertEqual(raster.dtypes, ("float32", "float32"))
                self.assertEqual(raster.descriptions, ("uo", "vo"))
                self.assertEqual(raster.nodata, -9999.0)
                self.assertEqual(raster.tags()["resampling"], "none")
                self.assertEqual(raster.tags()["source_checksum"], entry["source_checksum"])
                self.assertAlmostEqual(raster.transform.c, 129.5)
                self.assertAlmostEqual(raster.transform.f, 0.5)
                values = raster.read(masked=True)
                self.assertEqual(values.mask.shape, (2, 2, 3))
                self.assertTrue(np.array_equal(values.mask[0], values.mask[1]))
                self.assertTrue(bool(values.mask[:, 0, 2].all()))
                self.assertEqual(float(values[0, 1, 0]), 0.0)
            comparison = compare_job_outputs(
                root=folder,
                entry=entry,
                geotiff_dir=output_dir,
                prefix="fixture",
            )
            self.assertEqual(comparison["status"], "PASS_WITH_NOTES")
            self.assertEqual(comparison["file_count"], 2)
            self.assertLessEqual(comparison["max_absolute_difference"], 1e-6)
            self.assertIn("max_error_location", comparison)
            self.assertTrue(source.exists())

    def test_mask_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            _, entry, config = self._fixture(folder, mask_mismatch=True)
            with self.assertRaises(ConversionError):
                convert_job(
                    root=folder,
                    entry=entry,
                    output_dir=folder / "tiffs",
                    config_hash_value=config_hash([config], root=folder),
                    prefix="fixture",
                )

    def test_irregular_grid_fails_without_resampling(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            _, entry, config = self._fixture(folder, irregular_longitude=True)
            with self.assertRaisesRegex(ConversionError, "resampling"):
                convert_job(
                    root=folder,
                    entry=entry,
                    output_dir=folder / "tiffs",
                    config_hash_value=config_hash([config], root=folder),
                    prefix="fixture",
                )

    def test_source_checksum_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            _, entry, config = self._fixture(folder)
            entry["source_checksum"] = "0" * 64
            with self.assertRaises(ConversionError):
                convert_job(
                    root=folder,
                    entry=entry,
                    output_dir=folder / "tiffs",
                    config_hash_value=config_hash([config], root=folder),
                    prefix="fixture",
                )

    def test_comparator_detects_band_swap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            _, entry, config = self._fixture(folder)
            output_dir = folder / "tiffs"
            convert_job(
                root=folder,
                entry=entry,
                output_dir=output_dir,
                config_hash_value=config_hash([config], root=folder),
                prefix="fixture",
            )
            path = output_dir / "fixture_20200201T000000.tif"
            swapped = folder / "swapped.tif"
            with rasterio.open(path) as source:
                profile = source.profile
                data = source.read()[::-1]
                descriptions = source.descriptions
                tags = source.tags()
            with rasterio.open(swapped, "w", **profile) as destination:
                destination.write(data)
                destination.set_band_description(1, descriptions[1])
                destination.set_band_description(2, descriptions[0])
                destination.update_tags(**tags)
            path.unlink()
            swapped.rename(path)
            with self.assertRaises(ConversionError):
                compare_job_outputs(
                    root=folder,
                    entry=entry,
                    geotiff_dir=output_dir,
                    prefix="fixture",
                )

    def test_collection_conversion_inventory_audit_and_compare(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            _, entry, config = self._fixture(folder)
            second_entry = dict(entry)
            second_entry["job_id"] = "monthly_2020_02"
            second_entry["plan_name"] = "monthly"
            manifest = folder / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {"stage": "T4", "entries": [entry, second_entry]},
                    indent=2,
                ),
                encoding="utf-8",
            )
            output_root = folder / "collection"
            conversion = convert_collection(
                root=folder,
                manifest_path=manifest,
                output_root=output_root,
                config_hash_value=config_hash([config], root=folder),
                expected_job_count=2,
                expected_timestep_count=4,
            )
            self.assertEqual(conversion["job_count"], 2)
            self.assertEqual(conversion["timestep_count"], 4)
            audit = audit_collection_outputs(
                conversion_report=conversion,
                output_root=output_root,
            )
            self.assertEqual(audit["checked_output_count"], 4)
            comparison = compare_collection_outputs(
                root=folder,
                manifest_path=manifest,
                output_root=output_root,
            )
            self.assertEqual(comparison["file_count"], 4)
            self.assertLessEqual(comparison["max_absolute_difference"], 1e-6)


if __name__ == "__main__":
    unittest.main()
