"""Re-read one documented unit rejection using its original source packet."""

import argparse
import fcntl
import json
import re
from pathlib import Path

from . import guidance_margin_feed as feed
from . import guidance_margin_reader as reader
from .provenance import publish_bytes


def retry(root, event_id):
    if not re.fullmatch(r"[0-9a-f]{24}", event_id):
        raise ValueError("Invalid event")
    attempt = event_id + "-units-v2"
    original = root / "reader" / event_id
    with (root / ".feed.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads((root / "feed_state.json").read_text())
        entry = state["entries"][event_id]
        receipt = root / "unit_reviews" / (attempt + ".json")
        if entry.get("unit_review_attempt") == attempt:
            return entry["status"]
        if (
            entry["status"] != "EXTRACTION_REJECTED"
            or (root / "approved" / (event_id + ".json")).exists()
        ):
            raise ValueError("Only unadmitted source-reader rejections are eligible")
        status, output = reader._response_output(
            json.loads((original / "response.json").read_text())
        )
        if status != "CANDIDATE" or not any(
            val
            and val.get("unit") == "UNSUPPORTED"
            and re.search(r"\d\s*(?:[BbMm]\b|[Bb]illion\b|[Mm]illion\b)", json.dumps(val))
            for part in ("prior", "current")
            for metric in ("revenue", "operating_profit")
            for val in [output[part].get(metric)]
        ):
            raise ValueError("The original extraction has no documented unsupported USD scale")
        packet_path = original / "source_packet.json"
        packet = json.loads(packet_path.read_text())
        if (
            packet != json.loads((root / "packets" / (event_id + ".json")).read_text())
            or packet["event_id"] != event_id
        ):
            raise ValueError("Retained reader input differs from the saved packet")
        inv = json.loads((root / "inventory" / (event_id + ".json")).read_text())
        prior = packet["prior"]["source"]
        prior_records = [
            item
            for item in inv["releases"]
            if item["id"] == prior["id"] and item["text_sha256"] == prior["sha256"]
        ]
        if not inv["complete"] or len(prior_records) != 1:
            raise ValueError("Original inventory does not verify the prior")
        current_doc = feed.retained_for_review(root, entry)
        earlier = prior_records[0]
        prior_doc = feed.retained_for_review(
            root, dict(id=earlier["id"], url=earlier["url"], source_sha256=earlier["raw_sha256"])
        )
        current_doc["published_at"] = entry["published_at"]
        if packet["current"]["source"] != feed.as_packet_source(
            current_doc
        ) or prior != feed.as_packet_source(prior_doc):
            raise ValueError("Original source packet no longer matches both retained releases")
        if receipt.exists():
            evidence = json.loads(receipt.read_text())
            if evidence["prior_entry"] != entry:
                raise ValueError("Original queue row changed since intent")
        else:
            evidence = {
                "at": feed.now(),
                "prior_entry": entry,
                "attempt": attempt,
                "source_packet_sha256": feed.sha(packet_path.read_bytes()),
                "original_result_sha256": feed.sha((original / "result.json").read_bytes()),
            }
            publish_bytes(receipt, json.dumps(evidence, indent=2).encode())
        entry.update(
            unit_review_attempt=attempt,
            status="REVIEW_PENDING",
            reason="Corrected currency-unit reader pass started",
        )
        feed.write_json(root / "feed_state.json", state)
        try:
            feed.process_packet(root, state, entry, packet, inv, attempt)
        finally:
            feed.write_json(root / "feed_state.json", state)
            feed.status(root, state)
        return entry["status"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("event_id", nargs="+")
    args = parser.parse_args()
    for event in args.event_id:
        print(event, retry(args.state, event), flush=True)


if __name__ == "__main__":
    main()
