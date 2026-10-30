"""Read-only replay of frozen ledger cases, not a historical prediction generator.

Publication describes public availability; retrieval AND ledger recording describe
KOD's availability. Both clocks must pass. No network or writes, including migrations.
Hash checks establish local consistency only, not external timestamp authority.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

from ..hashing import fmt_ts, parse_ts, sha256_obj
from ..ledger import HORIZONS, LedgerError, freeze_card, frozen_evaluations


class ReplayUnavailable(ValueError):
    """The archive cannot support a trustworthy replay."""


def _time(value):
    try:
        return parse_ts(value)
    except (ValueError, TypeError, OverflowError):
        return None


def _available(cutoff, *values):
    times = [_time(value) for value in values]
    return cutoff is not None and all(value is not None and value <= cutoff for value in times)


class ReplayArchive:
    def __init__(self, db_path):
        self.db_path = Path(db_path).resolve()

    @contextmanager
    def _connection(self):
        try:
            connection = sqlite3.connect(self.db_path.as_uri() + '?mode=ro', uri=True)
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA query_only=ON')
            connection.execute('BEGIN')
        except sqlite3.Error as exc:
            raise ReplayUnavailable('Frozen ledger is unavailable; no database was created.') from exc
        try:
            yield connection
        except (sqlite3.Error, KeyError, TypeError, AttributeError, IndexError, json.JSONDecodeError, LedgerError) as exc:
            raise ReplayUnavailable('Frozen ledger is incomplete or inconsistent; replay withheld.') from exc
        finally:
            connection.close()

    def cases(self):
        """Navigation metadata only; never includes hypotheses, decisions or outcomes."""
        with self._connection() as db:
            return [dict(row) for row in db.execute(
                'SELECT case_id,symbol,call_type,decision_cutoff,opened_at FROM cases ORDER BY case_id'
            )]

    def snapshot(self, case_id, as_of, *, reveal_outcome=False, minimum_grade='D'):
        if minimum_grade not in ('A', 'B', 'C', 'D'):
            raise ValueError('Evidence threshold must be A, B, C or D.')
        cutoff = parse_ts(as_of)
        with self._connection() as db:
            return self._snapshot(db, case_id, cutoff, reveal_outcome, minimum_grade)

    def _snapshot(self, db, case_id, cutoff, reveal_outcome, minimum_grade):
        row = db.execute('SELECT * FROM cases WHERE case_id=?', (case_id,)).fetchone()
        if row is None:
            raise ReplayUnavailable('Unknown frozen case.')
        case = dict(row)
        sets = [dict(row) for row in db.execute(
            'SELECT * FROM information_sets WHERE case_id=? ORDER BY cutoff,horizon', (case_id,))]
        payloads = {row['horizon']: json.loads(row['payload_json']) for row in sets}
        evaluations = [dict(row) for row in db.execute(
            'SELECT * FROM detector_evaluations WHERE case_id=? ORDER BY detector,rule_version', (case_id,))]
        critics = [dict(row) for row in db.execute('SELECT * FROM critic_notes WHERE case_id=?', (case_id,))]
        if set(payloads) != set(HORIZONS) or len(sets) != 3 or len(critics) > 1:
            raise ReplayUnavailable('Frozen card has incomplete information sets or ambiguous critic records.')
        frozen = freeze_card(case, payloads, critics[0] if critics else None,
                             case.get('card_hash_version'), frozen_evaluations(evaluations))
        if sha256_obj(frozen) != case['card_sha']:
            raise ReplayUnavailable('Frozen card hash mismatch; replay withheld.')
        for item in sets:
            if sha256_obj(payloads[item['horizon']]) != item['set_sha'] or item['cutoff'] != payloads[item['horizon']].get('cutoff'):
                raise ReplayUnavailable('Information-set hash or cutoff mismatch; replay withheld.')
        opened = _time(case['opened_at'])
        if opened is None:
            raise ReplayUnavailable('Case recording chronology is missing; replay withheld.')
        # Revisions recorded later than the frozen open cannot support its original call.
        if any(_time(item['recorded_at']) != opened for item in sets + evaluations + critics):
            raise ReplayUnavailable('Frozen components do not share the case recording time.')

        visible_sets = []
        evidence = {}
        for item in sets:
            if not _available(cutoff, item['cutoff'], item['recorded_at']):
                continue
            payload = payloads[item['horizon']]
            visible_facts, withheld = {}, 0
            citations = payload.get('evidence', {})
            for key, value in sorted(payload.get('facts', {}).items()):
                ids = citations.get(key, [])
                supported = bool(ids) and isinstance(ids, list)
                known_ids = []
                for evidence_id in ids if isinstance(ids, list) else []:
                    if not isinstance(evidence_id, str):
                        supported = False
                        continue
                    source = db.execute('SELECT * FROM evidence_objects WHERE evidence_id=?', (evidence_id,)).fetchone()
                    if source is None:
                        supported = False
                        continue
                    obj = json.loads(source['object_json'])
                    if sha256_obj(obj) != evidence_id:
                        raise ReplayUnavailable('Evidence object hash mismatch; replay withheld.')
                    # Read chronology from hash-bound object, never mutable duplicated columns.
                    published, retrieved = obj.get('publication_time'), obj.get('retrieval_time')
                    if not _available(cutoff, published, retrieved, source['recorded_at']):
                        supported = False
                        continue
                    if (not _available(_time(retrieved), published)
                            or not _available(_time(source['recorded_at']), retrieved)
                            or not _available(opened, source['recorded_at'])):
                        supported = False
                        continue
                    if not _available(_time(item['cutoff']), published):
                        supported = False
                        continue
                    evidence[evidence_id] = {
                        'evidence_id': evidence_id, 'source_url': obj.get('source_url'),
                        'publisher': obj.get('publisher'), 'document_type': obj.get('document_type'),
                        'published_at': published, 'first_observed_at': retrieved,
                        'recorded_at': source['recorded_at'], 'grade': obj.get('evidence_grade'),
                        'publication_basis': obj.get('publication_time_basis'),
                    }
                    known_ids.append(evidence_id)
                if supported:
                    visible_facts[key] = {'value': value, 'evidence_ids': known_ids}
                else:
                    withheld += 1
            visible_sets.append({'horizon': item['horizon'], 'cutoff': item['cutoff'],
                                 'recorded_at': item['recorded_at'], 'facts': visible_facts,
                                 'withheld_fact_count': withheld})
        prediction = None
        if _available(cutoff, case['opened_at'], case['decision_cutoff']):
            prediction = {
                'label': 'Recorded prospective call' if case['call_type'] == 'PROSPECTIVE' else
                         ('Recorded retrospective reconstruction — not a historical forecast' if case['call_type'] == 'RETROSPECTIVE' else 'Recorded simulation — not a real forecast'),
                'recorded_at': case['opened_at'], 'decision_cutoff': case['decision_cutoff'],
                'disposition': case['disposition'], 'story_hypothesis': case['story_hypothesis'],
                'critic': frozen.get('critic'),
                'evaluations': frozen.get('detector_evaluations', []),
                'evaluation_note': 'Only evaluations bound into this card hash are shown. No recomputation.',
            }
        outcome = None
        outcome_status = 'Hidden. Reveal separately; nothing is loaded into this response.'
        if reveal_outcome:
            closed = db.execute('SELECT * FROM outcomes WHERE case_id=?', (case_id,)).fetchone()
            outcome_status = 'No outcome recorded by this cutoff.'
            if closed and _available(cutoff, closed['closed_at']):
                if closed['card_sha_at_open'] != case['card_sha']:
                    raise ReplayUnavailable('Outcome does not reference this frozen card.')
                if _time(closed['closed_at']) < opened:
                    raise ReplayUnavailable('Outcome recording precedes case recording.')
                outcome = dict(closed)
                outcome_status = 'Separately revealed recorded outcome; not an input to the snapshot.'
        known = [evidence[key] for key in sorted(evidence)]
        accepted = [item['evidence_id'] for item in known if item['grade'] in ('A', 'B', 'C', 'D') and item['grade'] <= minimum_grade]
        timeline = sorted({fmt_ts(t) for t in [_time(case['decision_cutoff']), opened] + [_time(item['cutoff']) for item in sets] if t is not None})
        snapshot = {
            'case': {key: case[key] for key in ('case_id', 'symbol', 'venue', 'call_type', 'decision_cutoff', 'opened_at', 'card_sha')},
            'as_of': cutoff.isoformat().replace('+00:00', 'Z'), 'timeline': timeline,
            'known_evidence': known, 'information_sets': visible_sets,
            'recorded_prediction': prediction,
            'integrity_note': 'Card and evidence-object hashes checked locally. External timestamp receipts and archived source bytes are not verified here.',
            'chronology_note': 'Facts require publication, retrieval and ledger recording by the cutoff. A historical publication date alone does not mean KOD had the evidence then.',
        }
        # The same read-only original has the same identity regardless of reveal/experiment.
        snapshot['snapshot_sha'] = sha256_obj(snapshot)
        snapshot['outcome'] = outcome
        snapshot['outcome_status'] = outcome_status
        snapshot['sandbox'] = {'minimum_grade': minimum_grade, 'accepted_evidence_ids': accepted,
                               'accepted_count': len(accepted), 'known_count': len(known),
                               'label': 'Sandbox evidence filter only — no prediction recalculation and no saved changes.'}
        return snapshot
