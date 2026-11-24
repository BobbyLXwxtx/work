import tempfile
import unittest
from pathlib import Path

from src.etl.fetch_and_normalize import (
    compute_diff,
    normalize_csv_rows,
    resolve_canadabuys_csv_url,
    write_outputs,
)


class TestCanadaBuysETL(unittest.TestCase):
    def setUp(self) -> None:
        header = (
            "referenceNumber-numeroReference,title-titre-eng,"
            "procurementCategory-categorieApprovisionnement,"
            "tenderStatus-appelOffresStatut-eng,"
            "publicationDate-datePublication,"
            "tenderClosingDate-appelOffresDateCloture,"
            "noticeURL-URLavis-eng"
        )
        rows = [
            f"CB-2026-00{i},Cloud Infrastructure Modernization #{i},SRV,Open,2026-11-24,2026-12-15,https://canadabuys.canada.ca/en/tender-opportunities/tender-notice/cb-{i}"
            for i in range(1, 8)
        ]
        self.sample_csv = "\n".join([header] + rows)

    def test_resolve_ckan_csv_url(self) -> None:
        ckan = {
            "result": {
                "resources": [
                    {"name": "Guide", "format": "HTML", "url": "https://example.com/guide"},
                    {"name": "New tender notices", "format": "CSV", "url": "https://example.com/new.csv"},
                ]
            }
        }
        self.assertEqual(resolve_canadabuys_csv_url(ckan), "https://example.com/new.csv")

    def test_normalize_and_diff(self) -> None:
        records = normalize_csv_rows(self.sample_csv)
        self.assertEqual(len(records), 7)
        diff = compute_diff(records, records[:5])
        self.assertEqual(len(diff["added"]), 2)
        self.assertEqual(len(diff["updated"]), 0)

    def test_self_healing_halt_on_small_feed(self) -> None:
        small_csv = "\n".join(self.sample_csv.splitlines()[:3])
        with self.assertRaises(RuntimeError):
            normalize_csv_rows(small_csv)

    def test_write_outputs(self) -> None:
        records = normalize_csv_rows(self.sample_csv)
        diff = compute_diff(records, [])
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp) / "dist"
            write_outputs(records, diff, dist, "https://polar.sh/checkout/canadabuys")
            self.assertTrue((dist / "index.html").exists())
            self.assertTrue((dist / "data" / "latest.json").exists())
            self.assertTrue((dist / "data" / "latest.csv").exists())
            html_text = (dist / "index.html").read_text(encoding="utf-8")
            self.assertIn("CanadaBuys Federal Tender Change Feed", html_text)


if __name__ == "__main__":
    unittest.main()