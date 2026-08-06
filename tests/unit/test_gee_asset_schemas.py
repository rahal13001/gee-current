from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read_schema(filename: str) -> dict:
    with (ROOT / "config" / filename).open(encoding="utf-8") as handle:
        return json.load(handle)


class GeeAssetSchemaTests(unittest.TestCase):
    def test_source_schema_is_closed_and_has_required_manifest_shape(self) -> None:
        schema = _read_schema("gee_source_asset.schema.json")

        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["required"],
            [
                "schema_version",
                "asset_role",
                "name",
                "tilesets",
                "bands",
                "properties",
                "startTime",
                "endTime",
            ],
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], "gee-source-asset-1.0")
        self.assertEqual(schema["properties"]["asset_role"]["const"], "source")

    def test_source_schema_preserves_uo_vo_order_and_required_provenance(self) -> None:
        schema = _read_schema("gee_source_asset.schema.json")
        bands = schema["properties"]["bands"]["prefixItems"]
        source_properties = schema["$defs"]["source_properties"]

        self.assertEqual(bands[0]["$ref"], "#/$defs/uo_band")
        self.assertEqual(bands[1]["$ref"], "#/$defs/vo_band")
        self.assertEqual(schema["$defs"]["uo_band"]["allOf"][1]["properties"]["tilesetBandIndex"]["const"], 0)
        self.assertEqual(schema["$defs"]["vo_band"]["allOf"][1]["properties"]["tilesetBandIndex"]["const"], 1)

        required = set(source_properties["required"])
        self.assertTrue(
            {
                "product_id",
                "dataset_id",
                "dataset_version",
                "dataset_part",
                "period_start",
                "period_end",
                "period_end_inclusive",
                "depth_m",
                "depth_label",
                "uo_units",
                "vo_units",
                "source_checksum",
                "source_grid",
                "mask_policy",
                "aoi_id",
                "created_utc",
            }.issubset(required)
        )
        self.assertEqual(source_properties["properties"]["period_end_inclusive"]["const"], False)
        self.assertEqual(source_properties["properties"]["depth_m"]["const"], 0.494025)
        self.assertEqual(source_properties["properties"]["direction_convention"]["const"], "towards_clockwise_from_north")

    def test_source_schema_separates_daily_jfm_and_monthly_collections(self) -> None:
        schema = _read_schema("gee_source_asset.schema.json")
        branches = schema["allOf"][0]["oneOf"]
        self.assertEqual(len(branches), 2)
        daily = branches[0]["properties"]["properties"]["properties"]
        monthly = branches[1]["properties"]["properties"]["properties"]
        self.assertEqual(daily["dataset_id"]["const"], "cmems_mod_glo_phy_my_0.083deg_P1D-m")
        self.assertEqual(daily["period_type"]["const"], "daily_jfm")
        self.assertEqual(monthly["dataset_id"]["const"], "cmems_mod_glo_phy_my_0.083deg_P1M-m")
        self.assertEqual(monthly["period_type"]["const"], "monthly_all")

    def test_derived_schema_is_closed_and_covers_local_product_types(self) -> None:
        schema = _read_schema("gee_derived_asset.schema.json")

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], "gee-derived-asset-1.0")
        self.assertEqual(schema["properties"]["asset_role"]["const"], "derived")
        self.assertEqual(schema["properties"]["bands"]["maxItems"], 1)

        product_types = schema["$defs"]["derived_properties"]["properties"]["product_type"]["enum"]
        self.assertEqual(
            set(product_types),
            {
                "monthly_climatology_speed",
                "jfm_climatology_speed",
                "speed",
                "speed_anomaly",
                "exploratory_trend_slope",
            },
        )

    def test_derived_schema_requires_provenance_mask_and_limitations(self) -> None:
        schema = _read_schema("gee_derived_asset.schema.json")
        required = set(schema["$defs"]["derived_properties"]["required"])

        self.assertTrue(
            {
                "analytics_version",
                "source_conversion_manifest",
                "source_conversion_manifest_sha256",
                "source_config_hash",
                "reference_period",
                "depth_m",
                "depth_label",
                "units",
                "source_grid",
                "mask_method",
                "mask_checksum",
                "limitation",
                "created_utc",
            }.issubset(required)
        )
        self.assertEqual(
            schema["$defs"]["derived_properties"]["properties"]["depth_m"]["const"],
            0.494025,
        )
        self.assertEqual(
            schema["allOf"][0]["oneOf"][-1]["properties"]["properties"]["properties"]["method"]["const"],
            "ordinary_least_squares_per_pixel",
        )


if __name__ == "__main__":
    unittest.main()
