"""Persistent research behavior, with no provider account or network required."""

from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest import mock

from kod.workstation.store import Store
from kod.workstation.services import ResearchService


PUBLISHED = "2024-11-20T21:00:00Z"
OBSERVED = "2024-11-20T21:05:00Z"
CUTOFF = "2024-11-20T22:00:00Z"
NOW = "2026-10-23T03:00:00Z"


def release(revenue="110"):
    return f"""<html><body>
<p>Acme Announces Financial Results for Third Quarter Fiscal 2025</p>
<p>Acme reported revenue for the third quarter ended October 27, 2024, of $0.1 billion.</p>
<table><tr><td>GAAP</td></tr>
<tr><td>($ in millions, except earnings per share)</td><td>Q3 FY25</td><td>Q2 FY25</td><td>Q3 FY24</td></tr>
<tr><td>Revenue</td><td>${revenue}</td><td>$100</td><td>$90</td></tr>
<tr><td>Diluted earnings per share</td><td>$1.10</td><td>$1.00</td><td>$0.90</td></tr>
</table></body></html>""".encode()


class CoreJourneyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "research"
        self.store = Store(self.root)
        self.service = ResearchService(self.store, clock=lambda: NOW)
        self.security = self.store.upsert_security("ACME", "Acme Corporation", cik="1234")

    def ingest(self, **kwargs):
        values = dict(
            security_id=self.security["id"], raw=release(), filename="earnings.htm",
            source_url="https://example.com/earnings.htm", published_at=PUBLISHED,
            retrieved_at=OBSERVED,
        )
        values.update(kwargs)
        return self.service.ingest(**values)

    def note(self):
        document = self.ingest()
        return self.service.generate_note(
            self.security["id"], document["id"], as_of=CUTOFF, mode="observed"
        )

    def test_security_identity_is_listing_scoped_not_ticker_only(self):
        other = self.store.upsert_security("ACME", "Different company", cik="5678", venue="XNYS")
        self.assertNotEqual(other["id"], self.security["id"])
        self.assertEqual(len(self.store.securities()), 2)

    def test_watchlist_removal_preserves_sources_and_readding_is_idempotent(self):
        document = self.ingest()
        self.store.remove_watchlist(self.security["id"])
        self.assertEqual(self.store.securities(), [])
        self.assertEqual(self.store.raw(document["id"]), release())
        again = self.store.upsert_security("ACME", "Acme Corporation", cik="1234")
        self.assertEqual(again["id"], self.security["id"])
        self.assertEqual(len(self.store.securities()), 1)

    def test_same_listing_cannot_silently_change_to_another_known_issuer(self):
        with self.assertRaises(ValueError):
            self.store.upsert_security("ACME", "Another issuer", cik="9999")
        self.assertEqual(int(self.store.get_security(self.security["id"])["cik"]), 1234)

    def test_ingest_preserves_exact_bytes_hash_and_association(self):
        document = self.ingest()
        self.assertEqual(document["extraction_status"], "parsed")
        self.assertEqual(document["sha256"], hashlib.sha256(release()).hexdigest())
        self.assertEqual(self.store.raw(document["id"]), release())
        self.assertEqual(document["association"], "user_asserted")

    def test_same_source_and_content_are_idempotent_without_erasing_first_observation(self):
        first = self.ingest()
        second = self.ingest(retrieved_at="2024-11-20T21:10:00Z")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.store.documents(self.security["id"])), 1)
        self.assertEqual(self.store.document(first["id"])["observed_at"], OBSERVED)
        self.assertEqual(second["observation_count"], 2)
        self.assertEqual(second["last_observed_at"], "2024-11-20T21:10:00Z")

    def test_changed_bytes_at_same_url_create_a_version_and_retain_original(self):
        first = self.ingest()
        second = self.ingest(raw=release("115"), retrieved_at="2024-11-20T21:10:00Z")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(len(self.store.documents(self.security["id"])), 2)
        self.assertEqual(self.store.raw(first["id"]), release())
        self.assertEqual(self.store.raw(second["id"]), release("115"))

    def test_parser_upgrade_can_reparse_previously_unsupported_bytes_without_erasing_old_version(self):
        self.service.parser_sha256 = "1" * 64
        with mock.patch("kod.workstation.services.earnings.choose_current", return_value=None):
            old = self.ingest()
        self.assertEqual(old["extraction_status"], "unsupported")
        self.service.parser_sha256 = "2" * 64
        new = self.ingest()
        self.assertNotEqual(old["id"], new["id"])
        self.assertEqual(new["extraction_status"], "parsed")
        self.assertEqual(self.store.document(old["id"])["extraction_status"], "unsupported")
        self.assertEqual(self.store.raw(old["id"]), self.store.raw(new["id"]))

    def test_unsupported_document_is_retained_but_cannot_generate_false_facts(self):
        raw = b"<html><body><p>A press release with no supported financial table.</p></body></html>"
        document = self.ingest(raw=raw)
        self.assertEqual(document["extraction_status"], "unsupported")
        self.assertEqual(self.store.raw(document["id"]), raw)
        with self.assertRaises(ValueError):
            self.service.generate_note(self.security["id"], document["id"], as_of=CUTOFF)
        self.assertEqual(self.store.notes(), [])

    def test_known_sec_url_cik_mismatch_is_rejected_before_storage(self):
        with self.assertRaises(ValueError):
            self.ingest(source_url="https://www.sec.gov/Archives/edgar/data/320193/000032019324000120/apple.htm")
        self.assertEqual(self.store.documents(), [])

    def test_matching_official_looking_url_is_still_user_asserted(self):
        document = self.ingest(source_url="https://www.sec.gov/Archives/edgar/data/1234/000000123424000001/earnings.htm")
        self.assertEqual(document["association"], "user_asserted")

    def test_later_identity_resolution_revalidates_current_and_comparison_sources(self):
        unknown = self.store.upsert_security("AMD", "Advanced Micro Devices", cik=None)
        wrong = self.ingest(security_id=unknown["id"], source_url="https://www.sec.gov/Archives/edgar/data/320193/000032019324000120/apple.htm")
        correct = self.ingest(security_id=unknown["id"], source_url="https://www.sec.gov/Archives/edgar/data/2488/000000248824000161/amd.htm")
        self.store.upsert_security("AMD", "Advanced Micro Devices", cik="2488")
        for current_id, comparison_id in ((wrong["id"], None), (correct["id"], wrong["id"])):
            with self.subTest(current=current_id), self.assertRaises(ValueError):
                self.service.generate_note(unknown["id"], current_id, comparison_id, as_of=CUTOFF)
        self.assertEqual(len(self.store.notes(unknown["id"])), 0)

    def test_later_identity_resolution_checks_preserved_header_evidence(self):
        unknown = self.store.upsert_security("AMD", "Advanced Micro Devices", cik=None)
        document = self.ingest(security_id=unknown["id"], sec_headers=b"CENTRAL INDEX KEY: 0000320193")
        self.store.upsert_security("AMD", "Advanced Micro Devices", cik="2488")
        with self.assertRaises(ValueError):
            self.service.generate_note(unknown["id"], document["id"], as_of=CUTOFF)

    def test_fact_evidence_uses_actual_stored_document_and_version_identity(self):
        note = self.note()
        evidence = note["result"]["facts"][0]["evidence"]
        self.assertEqual(evidence["document_id"], note["current_document_id"])
        self.assertEqual(evidence["source_version_id"], note["current_document_id"])

    def test_invalid_timestamp_and_unsafe_source_scheme_are_rejected(self):
        for kwargs in (
            {"published_at": "2024-11-20T21:00:00"},
            {"retrieved_at": "2024-11-20T21:05:00"},
            {"source_url": "javascript:alert(1)"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.ingest(**kwargs)

    def test_date_only_publication_is_not_promoted_to_midnight(self):
        document = self.ingest(published_at="2024-11-20")
        self.assertIsNone(document["published_at"])
        self.assertEqual(document["metadata"]["publication_date"], "2024-11-20")
        note = self.service.generate_note(self.security["id"], document["id"], as_of=CUTOFF, mode="public")
        self.assertEqual(note["result"]["facts"], [])

    def test_observation_cannot_precede_its_known_publication(self):
        with self.assertRaises(ValueError):
            self.ingest(retrieved_at="2024-11-20T20:00:00Z")
        self.assertEqual(self.store.documents(), [])

    def test_cutoff_exclusion_does_not_expose_hidden_headline_figures(self):
        document = self.ingest()
        note = self.service.generate_note(
            self.security["id"], document["id"], as_of="2024-11-20T20:59:00Z", mode="public"
        )
        result = note["result"]
        self.assertEqual(result["facts"], [])
        self.assertFalse(result["cutoff"]["current_release_eligible"])
        self.assertNotIn("$0.1 billion", json.dumps(result))
        self.assertNotIn("| Revenue |", note["markdown"])

    def test_later_retrieval_is_public_reconstruction_only(self):
        document = self.ingest(retrieved_at=NOW)
        observed = self.service.generate_note(self.security["id"], document["id"], as_of=CUTOFF, mode="observed")
        public = self.service.generate_note(self.security["id"], document["id"], as_of=CUTOFF, mode="public")
        self.assertEqual(observed["result"]["facts"], [])
        self.assertTrue(public["result"]["facts"])
        self.assertIn("Historical reconstruction", public["markdown"])

    def test_same_note_inputs_are_idempotent_and_real_values_have_evidence(self):
        first = self.note()
        second = self.note()
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.store.notes()), 1)
        revenue = next(f for f in first["result"]["facts"] if f["metric"] == "revenue")
        self.assertEqual(revenue["value"], "110")
        self.assertIn("Revenue", revenue["evidence"]["quote"])
        self.assertFalse(first["result"]["entry_permission"])
        self.assertIn("CONSENSUS UNKNOWN", first["markdown"])

    def test_listing_currency_does_not_silently_override_reporting_currency(self):
        self.store.upsert_security("ACME", "Acme Corporation", cik="1234", currency="CAD")
        note = self.note()
        revenue = next(f for f in note["result"]["facts"] if f["metric"] == "revenue")
        self.assertEqual(revenue["currency"], "USD")
        self.assertIn("CURRENCY_ASSUMED_USD_FROM_$_SIGN", revenue["flags"])

    def test_changing_listing_currency_cannot_reinterpret_preserved_reporting_figures(self):
        document = self.ingest()
        first = self.service.generate_note(self.security["id"], document["id"], as_of=CUTOFF)
        self.store.upsert_security("ACME", "Acme Corporation", cik="1234", currency="CAD")
        second = self.service.generate_note(self.security["id"], document["id"], as_of=CUTOFF)
        before = next(f for f in first["result"]["facts"] if f["metric"] == "revenue")
        after = next(f for f in second["result"]["facts"] if f["metric"] == "revenue")
        self.assertEqual((before["currency"], before["value"]), (after["currency"], after["value"]))

    def test_document_ownership_checked_for_current_and_comparison(self):
        document = self.ingest()
        other = self.store.upsert_security("OTHER", "Other Corporation", cik="5678")
        foreign = self.ingest(security_id=other["id"])
        with self.assertRaises(ValueError):
            self.service.generate_note(other["id"], document["id"], as_of=CUTOFF)
        with self.assertRaises(ValueError):
            self.service.generate_note(self.security["id"], document["id"], foreign["id"], as_of=CUTOFF)

    def test_annotation_versions_and_note_survive_restart(self):
        note = self.note()
        self.store.annotate(note["id"], "Revenue improved", "Revenue is restated lower", "Next earnings release")
        self.store.annotate(note["id"], "Await margin explanation", "Management retracts guidance", "Read the original reconciliation")
        reopened = Store(self.root)
        self.assertEqual(reopened.note(note["id"])["result"]["period"], "Q3 FY25")
        annotations = reopened.annotations(note["id"])
        self.assertEqual(len(annotations), 2)
        self.assertEqual(annotations[0]["thesis"], "Await margin explanation")
        self.assertEqual(annotations[1]["thesis"], "Revenue improved")

    def test_core_journey_never_opens_a_network_connection(self):
        with mock.patch("socket.socket", side_effect=AssertionError("network forbidden")):
            note = self.note()
            self.assertTrue(note["result"]["facts"])

    def test_events_are_idempotent_and_keep_source_association(self):
        document = self.ingest()
        values = dict(
            security_id=self.security["id"], external_id="0000001234-24-000001", form="8-K",
            title="Results", source_url="https://example.com/filing.htm", published_at=PUBLISHED,
            observed_at=OBSERVED, document_id=document["id"],
        )
        first = self.store.save_event(**values)
        second = self.store.save_event(**values)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.store.events(self.security["id"])), 1)
        self.assertEqual(self.store.events()[0]["document_id"], document["id"])

    def test_event_cannot_attach_another_securitys_document(self):
        document = self.ingest()
        other = self.store.upsert_security("OTHER", "Other Corporation", cik="5678")
        with self.assertRaises(ValueError):
            self.store.save_event(other["id"], "event-1", "8-K", "Results", "https://example.com/filing.htm", document_id=document["id"])
        self.assertEqual(self.store.events(), [])

    def test_last_success_survives_later_failed_refresh(self):
        self.store.record_job("sec", self.security["id"], "success", "No new events", started_at=OBSERVED, finished_at=CUTOFF)
        self.store.record_job("sec", self.security["id"], "failed", "Provider unavailable", started_at=NOW, finished_at=NOW)
        health = next(h for h in self.store.health() if h["provider"] == "sec")
        self.assertEqual(health["status"], "failed")
        self.assertTrue(health["last_success"])
        self.assertIn("Provider unavailable", health["message"])

    def test_backup_restore_recovers_source_note_and_annotation(self):
        note = self.note()
        self.store.annotate(note["id"], "Inspect economics", "Facts are restated", "Next quarter")
        backup = self.store.backup(self.base / "backup")
        restored = Store.restore(backup, self.base / "restored")
        self.assertEqual(restored.note(note["id"])["markdown"], note["markdown"])
        self.assertEqual(restored.raw(note["current_document_id"]), release())
        self.assertEqual(restored.annotations(note["id"])[0]["thesis"], "Inspect economics")
        self.assertEqual(len(restored.securities()), 1)

    def test_restore_and_backup_refuse_existing_target_without_erasing_it(self):
        self.note()
        backup = self.store.backup(self.base / "backup")
        target = self.base / "existing"
        target.mkdir()
        marker = target / "valuable.txt"
        marker.write_text("preserve this")
        with self.assertRaises(ValueError):
            Store.restore(backup, target)
        with self.assertRaises(ValueError):
            self.store.backup(target)
        self.assertEqual(marker.read_text(), "preserve this")

    def test_source_hash_tampering_is_detected(self):
        document = self.ingest()
        originals = [p for p in self.root.rglob("*") if p.is_file() and p.read_bytes() == release()]
        self.assertEqual(len(originals), 1)
        originals[0].write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            self.store.raw(document["id"])

    def test_restore_rejects_tampered_backup_before_creating_target(self):
        self.note()
        backup = self.store.backup(self.base / "backup")
        objects = [p for p in backup.rglob("*") if p.is_file() and p.read_bytes() == release()]
        self.assertEqual(len(objects), 1)
        objects[0].write_bytes(b"tampered backup object")
        target = self.base / "restored"
        with self.assertRaises(ValueError):
            Store.restore(backup, target)
        self.assertFalse(target.exists())

    def test_restore_rejects_symlinked_evidence_ancestor(self):
        self.note()
        backup = self.store.backup(self.base / "backup")
        actual_objects = self.base / "objects-elsewhere"
        (backup / "objects").rename(actual_objects)
        (backup / "objects").symlink_to(actual_objects, target_is_directory=True)
        target = self.base / "restored"
        with self.assertRaises(ValueError):
            Store.restore(backup, target)
        self.assertFalse(target.exists())

    def test_mutable_store_refuses_legacy_frozen_record_destinations(self):
        backup = self.store.backup(self.base / "valid-backup")
        for suffix in ("kod-machine/registry/cards", "kod-machine/var", "idx-signals/research", "idx-signals/data/manifests"):
            operations = {
                "create": Store,
                "backup": self.store.backup,
                "restore": lambda target: Store.restore(backup, target),
            }
            for name, operation in operations.items():
                root = self.base / "legacy-checkout" / suffix / name
                with self.subTest(path=suffix, operation=name):
                    with self.assertRaises(ValueError):
                        operation(root)
                    self.assertFalse(root.exists(), suffix)


if __name__ == "__main__":
    unittest.main()
