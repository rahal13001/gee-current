from __future__ import annotations

import csv
from pathlib import Path
import tempfile
import unittest

from python.checksum import (
    CHECKSUM_COLUMNS,
    ChecksumError,
    generate_job_checksums,
    sha256_file,
    verify_sha256,
    write_checksum_csv,
)
from python.inventory import InventoryStore


def _job(job_id: str) -> dict[str, object]:
    return {
        "job_id": job_id,
        "plan_name": "monthly_all",
        "dataset_id": "cmems_mod_glo_phy_my_0.083deg_P1M-m",
        "year": 2015,
        "month": 1,
        "start_datetime": "2015-01-01T00:00:00",
        "end_datetime": "2015-01-31T23:59:59",
        "expected_timesteps": 1,
        "output_directory": "data/raw/monthly/2015",
        "output_filename": f"{job_id}.nc",
        "status": "planned",
        "attempt_count": 0,
        "checksum": "",
        "dataset_version": "202311",
        "dataset_part": "default",
        "created_utc": "2026-08-04T00:00:00Z",
    }


class Stage3ChecksumTests(unittest.TestCase):
    def test_sha256_is_stable_and_64_lowercase_hex(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            target = Path(folder.name) / "fixture.bin"
            target.write_bytes(b"GLORYS checksum fixture\n")
            first = sha256_file(target, chunk_size=1)
            second = sha256_file(target, chunk_size=1)
            self.assertEqual(first, second)
            self.assertRegex(first, r"^[0-9a-f]{64}$")
            self.assertTrue(verify_sha256(target, first, chunk_size=1))
            target.write_bytes(b"GLORYS checksum fixture!")
            self.assertFalse(verify_sha256(target, first, chunk_size=1))
            with self.assertRaises(ChecksumError):
                verify_sha256(target, "not-a-sha256")
        finally:
            folder.cleanup()

    def test_job_checksums_are_sorted_and_include_required_manifest_fields(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            output_directory = Path(folder.name) / "data/raw/monthly/2015"
            output_directory.mkdir(parents=True)
            (output_directory / "job_b.nc").write_bytes(b"b")
            (output_directory / "job_a.nc").write_bytes(b"a")
            with InventoryStore(Path(folder.name) / "inventory.sqlite") as store:
                store.seed_jobs([_job("job_b"), _job("job_a")])
                records = generate_job_checksums(
                    store.list_jobs(),
                    root=folder.name,
                    calculated_utc="2026-08-04T00:00:00Z",
                    chunk_size=1,
                )
            self.assertEqual(tuple(record.job_id for record in records), ("job_a", "job_b"))
            self.assertEqual(records[0].relative_path, "data/raw/monthly/2015/job_a.nc")
            self.assertEqual(records[0].size_bytes, 1)
            self.assertRegex(records[0].sha256, r"^[0-9a-f]{64}$")
            self.assertEqual(records[0].calculated_utc, "2026-08-04T00:00:00Z")
        finally:
            folder.cleanup()

    def test_manifest_csv_has_normative_columns_and_deterministic_rows(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            output_directory = Path(folder.name) / "data/raw/monthly/2015"
            output_directory.mkdir(parents=True)
            (output_directory / "job_b.nc").write_bytes(b"b")
            (output_directory / "job_a.nc").write_bytes(b"a")
            with InventoryStore(Path(folder.name) / "inventory.sqlite") as store:
                store.seed_jobs([_job("job_b"), _job("job_a")])
                records = generate_job_checksums(
                    store.list_jobs(), root=folder.name, calculated_utc="2026-08-04T00:00:00Z"
                )
            manifest = write_checksum_csv(records, Path(folder.name) / "outputs/checksums/sha256.csv")
            with manifest.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
            self.assertEqual(reader.fieldnames, list(CHECKSUM_COLUMNS))
            self.assertEqual([row["job_id"] for row in rows], ["job_a", "job_b"])
            self.assertEqual(rows[0]["size_bytes"], "1")
            self.assertRegex(rows[0]["sha256"], r"^[0-9a-f]{64}$")
        finally:
            folder.cleanup()

    def test_missing_file_and_path_escape_fail_closed(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            with InventoryStore(Path(folder.name) / "inventory.sqlite") as store:
                store.seed_jobs([_job("missing")])
                with self.assertRaises(ChecksumError):
                    generate_job_checksums(store.list_jobs(), root=folder.name)

                escape = _job("escape")
                escape["output_directory"] = ".."
                store.seed_jobs([escape])
                with self.assertRaises(ChecksumError):
                    generate_job_checksums((store.get_job("escape"),), root=folder.name)
        finally:
            folder.cleanup()

    def test_invalid_chunk_size_and_duplicate_job_ids_fail_closed(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            target = Path(folder.name) / "fixture.bin"
            target.write_bytes(b"fixture")
            with self.assertRaises(ChecksumError):
                sha256_file(target, chunk_size=0)
            with InventoryStore(Path(folder.name) / "inventory.sqlite") as store:
                store.seed_jobs([_job("duplicate")])
                job = store.get_job("duplicate")
                with self.assertRaises(ChecksumError):
                    generate_job_checksums((job, job), root=folder.name)
        finally:
            folder.cleanup()


if __name__ == "__main__":
    unittest.main()
