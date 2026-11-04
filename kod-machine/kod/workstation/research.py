"""Small read-only boundary from historical research artifacts to workstation views.

No idxsig imports, execution, model fitting, network, or archive writes. Source text
is data. Original bytes and exploratory view state are never conflated.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

from ..hashing import parse_ts


class ResearchUnavailable(ValueError):
    """A research artifact cannot safely support this view."""


def _clean(value):
    # Historical execution archives used Infinity as an unbounded cost-tier cap.
    # Preserve its meaning as text, never as a numeric performance measurement.
    if isinstance(value, float) and not math.isfinite(value):
        return 'unbounded' if value == float('inf') else 'non-finite (unavailable)'
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


class ResearchArchive:
    """Pinned artifacts; root overrides exist for offline import/testing, not URLs."""

    def __init__(self, root=None):
        self.root = Path(root) if root is not None else Path(__file__).with_name('research_evidence')

    def _entries(self):
        try:
            entries = json.loads((self.root / 'manifest.json').read_text(encoding='utf-8'))
            if not isinstance(entries, list):
                raise ValueError('manifest must be a list')
            ids = set()
            for entry in entries:
                if not isinstance(entry, dict) or not re.fullmatch(r'[a-z0-9_-]+', entry['id']):
                    raise ValueError('invalid catalog id')
                if entry['id'] in ids:
                    raise ValueError('duplicate catalog id')
                ids.add(entry['id'])
                if not re.fullmatch(r'[0-9a-f]{64}', entry['sha256']):
                    raise ValueError('missing digest')
                if not re.fullmatch(r'[0-9a-f]{40}', entry['commit']):
                    raise ValueError('missing pinned commit')
                if not isinstance(entry['title'], str) or not isinstance(entry['path'], str):
                    raise ValueError('invalid source metadata')
                if not entry['path'].startswith('idx-signals/') or '..' in entry['path'].split('/'):
                    raise ValueError('invalid source path')
                parse_ts(entry['captured_at'])
            return entries
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ResearchUnavailable('Research catalog is missing or malformed; no data invented.') from exc

    def studies(self):
        return [{'study_id': e['id'], 'title': e['title'], 'kind': 'retrospective research',
                 'captured_at': e['captured_at']} for e in self._entries()]

    def study(self, study_id, as_of=None):
        if not isinstance(study_id, str) or not re.fullmatch(r'[a-z0-9_-]+', study_id):
            raise ResearchUnavailable('Invalid research study id.')
        entry = next((e for e in self._entries() if e['id'] == study_id), None)
        if entry is None:
            raise ResearchUnavailable('Unknown research study.')
        path = self.root / (study_id + '.json')
        try:
            # Refuse symlink escapes, including caller-supplied offline catalogs.
            if path.resolve().parent != self.root.resolve():
                raise ValueError('artifact escapes catalog')
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('artifact digest mismatch')
            raw = json.loads(data)
            if not isinstance(raw, dict):
                raise ValueError('artifact must be an object')
            recorded = raw.get('created_at') or raw.get('finished')
            recorded_time = parse_ts(recorded)
            captured_time = parse_ts(entry['captured_at'])
            cutoff = parse_ts(as_of) if as_of is not None else None
            self._validate(study_id, raw)
        except (OSError, ValueError, KeyError, TypeError, OverflowError, AttributeError, IndexError) as exc:
            raise ResearchUnavailable('Research artifact is missing, inconsistent or unsupported; metrics withheld.') from exc
        result = {
            'study_id': study_id, 'title': entry['title'], 'status': 'available',
            'kind': 'retrospective research', 'recorded_at': recorded,
            'captured_at': entry['captured_at'], 'as_of': as_of,
            'source': {'path': entry['path'], 'commit': entry['commit'], 'sha256': entry['sha256'],
                       'url': 'https://github.com/jonathanpratama-boop/KOD-Machine/blob/' + entry['commit'] + '/' + entry['path']},
            'chronology_note': 'Historical research, not a prospective forecast. Computation time is not observation time. As-of views require both computation and this archive capture by the cutoff.',
            'integrity_note': 'Exact source bytes match the catalog SHA-256. This is local consistency, not external timestamp authority or independent validation of the study.',
            'reproduction': {'command': None, 'inputs': None, 'source_artifacts': [entry['path']], 'limits': 'Exact reproduction command and input data are not bundled. Source hashes identify archived inputs; this adapter does not rerun or independently reproduce research.'},
            'invariants': ['Original source bytes remain read-only.', 'No automatic case-to-population association.', 'Computation and capture must both precede the cutoff.', 'No model fitting, experiment rerun or trade execution.'],
            'population': {}, 'baselines': {}, 'uncertainty': {}, 'calibration': {}, 'execution': {},
            'limitations': ['No automatic case, ticker or population membership is asserted.',
                            'Detection, probability calibration and executable profit are different claims.',
                            'No live performance, untouched-holdout or trade authorization claim.'],
        }
        if cutoff is not None and max(recorded_time, captured_time) > cutoff:
            result['status'] = 'withheld'
            result.pop('source')
            result.pop('reproduction')
            result['limitations'].append('Artifact was not both computed and captured by this cutoff; metrics and raw contents are withheld.')
            return result
        if study_id == 'sequence':
            result.update(population={'test': raw['test'], 'shortlists': raw['shortlists'], 'fit_periods': raw['fit_periods']},
                          baselines={'comparison': 'simple / g2 / summary / sequence at the same selection budget',
                                     'probability_metrics': raw['probability_metrics']},
                          uncertainty=raw['paired_precision_differences'], calibration=raw['calibration'],
                          execution={'status': 'not tested by this model comparison'})
            result['limitations'] += [raw['interpretation'], 'Censored alerts are separate from known false alerts. Precision bounds are not confidence intervals.',
                                      'Historical model comparison alone cannot establish prospective trading advantage.']
            ci = raw['paired_precision_differences']['early']['sequence_minus_summary']
            crosses_zero = ci['lower95'] <= 0 <= ci['upper95']
            result['comparison_conclusion'] = 'Not established' if crosses_zero else 'Recorded interval excludes zero'
            result['comparison_note'] = ('Paired interval includes zero.' if crosses_zero else 'Paired interval excludes zero in this historical comparison.') + ' Research challenger, not an active policy.'
        elif study_id == 'e6':
            result.update(population={'eligible_coin_days': raw['eligible_coin_days'], 'period': raw['period'],
                                      'arms': raw['arms']}, baselines={'comparisons': raw['comparisons']},
                          uncertainty={name: arm['vs_matched'] for name, arm in raw['arms'].items()},
                          execution={'status': 'failed discovery; frozen, not reopened', 'gates': raw['gates'],
                                     'stage2': raw['stage2'], 'claims': raw['claims']},
                          calibration={'status': 'not supplied'})
            result['limitations'].append('Both registered E6 discovery gates failed. No validation or new experiment is run here.')
        elif study_id == 'execution':
            result.update(population={'universe': raw['universe'], 'signals': raw['signals'], 'rule_trades': raw['rule_trades']},
                          baselines={'matched': raw['random_matched'], 'same_session': raw['random']},
                          uncertainty={'note': 'Random-draw percentiles describe baseline draws, not a paired confidence interval.'},
                          execution={'assumptions': raw['execution'], 'config': raw['config'], 'market': raw['market']},
                          calibration={'status': 'not supplied'})
            result['limitations'] += raw['warnings'] + raw['data_quality']['known_limitations']
        else:
            raise ResearchUnavailable('Unsupported research schema.')
        result['raw'] = raw
        return _clean(result)

    @staticmethod
    def _validate(study_id, raw):
        def number(value, low=None, high=None):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('required finite numeric field missing or invalid')
            if (low is not None and value < low) or (high is not None and value > high):
                raise ValueError('numeric field outside its domain')
            return value

        def counts(obj, names):
            for name in names:
                if not _count(obj[name]):
                    raise ValueError('invalid population count')

        def interval(obj, low='lower95', high='upper95', estimate='delta'):
            lo, hi = number(obj[low]), number(obj[high])
            number(obj[estimate])
            if lo > hi:
                raise ValueError('reversed interval')

        def finite_tree(obj, path=()):
            if isinstance(obj, dict):
                for k, v in obj.items(): finite_tree(v, path + (k,))
            elif isinstance(obj, list):
                for i, v in enumerate(obj): finite_tree(v, path + (i,))
            elif isinstance(obj, float) and not math.isfinite(obj):
                # Only the known legacy unbounded execution cost-tier cap is valid.
                if not (study_id == 'execution' and len(path) == 4 and path[:2] == ('execution','cost_tiers') and path[3] == 0 and obj == float('inf')):
                    raise ValueError('nonfinite research metric')

        finite_tree(raw)
        if study_id == 'sequence':
            for field in ('test', 'shortlists', 'fit_periods', 'probability_metrics', 'paired_precision_differences', 'calibration'):
                if not isinstance(raw[field], dict):
                    raise ValueError('invalid sequence schema')
            counts(raw['test'], ('censored_rows','decision_days','eligible_rows','known_rows','tickers'))
            if raw['test']['known_rows'] + raw['test']['censored_rows'] != raw['test']['eligible_rows']:
                raise ValueError('inconsistent test population')
            for cohort in ('all', 'early'):
                for model in ('sequence', 'summary', 'simple', 'g2'):
                    row = raw['shortlists'][cohort][model]
                    counts(row, ('selected','known_selected','up_hits','false_alerts_known','censored_selected',
                                 'episodes_caught','episodes_missed','known_episodes','candidate_windows','calendar_days'))
                    if row['up_hits'] + row['false_alerts_known'] != row['known_selected'] or row['known_selected'] + row['censored_selected'] != row['selected']:
                        raise ValueError('inconsistent alert denominators')
                    if row['episodes_caught'] + row['episodes_missed'] != row['known_episodes']:
                        raise ValueError('inconsistent episode denominators')
                    if not 0 < row['known_selected'] <= row['selected'] <= row['candidate_windows'] or row['known_episodes'] <= 0:
                        raise ValueError('invalid denominator')
                    expected = {'precision_known': row['up_hits']/row['known_selected'],
                                'precision_lower_bound': row['up_hits']/row['selected'],
                                'precision_upper_bound': (row['up_hits']+row['censored_selected'])/row['selected'],
                                'episode_recall_known': row['episodes_caught']/row['known_episodes']}
                    for key, ratio in expected.items():
                        if not math.isclose(number(row[key],0,1), ratio, rel_tol=1e-8, abs_tol=1e-10):
                            raise ValueError('ratio does not match denominator')
                for comparison in ('sequence_minus_simple','sequence_minus_summary'):
                    ci=raw['paired_precision_differences'][cohort][comparison]
                    interval(ci)
                    counts(ci, ('block_days','draws','seed'))
                    if ci['block_days'] == 0 or ci['draws'] == 0:
                        raise ValueError('empty uncertainty method')
            for model in ('sequence','summary','train_base_rate'):
                scores=raw['probability_metrics'][model]
                counts(scores, ('n',))
                if scores['n'] != raw['test']['known_rows']:
                    raise ValueError('probability denominator differs')
                number(scores['log_loss'],0)
                number(scores['brier_multiclass'],0,2)
                number(scores['up_brier'],0,1)
            for model in ('sequence','summary'):
                calibration=raw['calibration'][model]
                if number(calibration['temperature'],0) == 0:
                    raise ValueError('invalid calibration temperature')
                losses=calibration['candidate_log_losses']
                if not isinstance(losses,dict) or not losses:
                    raise ValueError('missing calibration trials')
                for loss in losses.values(): number(loss,0)
            for stage in ('train','calibration'):
                fit=raw['fit_periods'][stage]
                counts(fit, ('rows',))
                counts(fit['class_counts'], ('down_first','neither','up_first'))
                if sum(fit['class_counts'].values()) != fit['rows']:
                    raise ValueError('invalid fit denominator')
            if not isinstance(raw['interpretation'], str):
                raise ValueError('missing interpretation')
        elif study_id == 'e6':
            counts(raw, ('eligible_coin_days',))
            if not isinstance(raw['arms'],dict) or not raw['arms']:
                raise ValueError('missing E6 arms')
            for name in ('P1_pressure','P2_pressure_then_breakout'):
                if raw['gates'][name]['passed'] is not False or not isinstance(raw['gates'][name]['reasons'],list):
                    raise ValueError('frozen failed gate changed')
            if not isinstance(raw['period'],list) or len(raw['period']) != 2:
                raise ValueError('invalid E6 period')
            for name in ('stage2','claims'):
                if not isinstance(raw[name],str): raise ValueError('invalid E6 metadata')
            for arm in raw['arms'].values():
                counts(arm, ('flags','scored','no_entry','no_controls','missing_end','distinct_coins'))
                if arm['scored'] > arm['flags']:
                    raise ValueError('scored exceeds flagged population')
                for key in ('mean_R120','median_R120','mean_ctrl_R120','mean_excess','E30_lift'): number(arm[key])
                for key in ('E30_rate','E30_ctrl_rate'): number(arm[key],0,1)
                ci=arm['vs_matched']
                pair=ci['ci95']
                if not isinstance(pair,list) or len(pair)!=2 or number(pair[0])>number(pair[1]):
                    raise ValueError('invalid matched interval')
                number(ci['estimate']);number(ci['p_one_sided'],0,1)
            if not isinstance(raw['comparisons'],dict) or not raw['comparisons']:
                raise ValueError('missing E6 comparisons')
            for ci in raw['comparisons'].values():
                pair=ci['ci95']
                if not isinstance(pair,list) or len(pair)!=2 or number(pair[0])>number(pair[1]):
                    raise ValueError('invalid comparison interval')
                number(ci['estimate']);number(ci['p_one_sided'],0,1)
        elif study_id == 'execution':
            for field in ('universe','signals','rule_trades','random_matched','random','execution','config','market','data_quality'):
                if not isinstance(raw[field],dict): raise ValueError('invalid execution schema')
            r=raw['rule_trades']
            counts(r, ('attempts','filled','scored','liquidated'))
            if not r['liquidated'] <= r['scored'] <= r['filled'] <= r['attempts']:
                raise ValueError('inconsistent execution denominators')
            number(r['hit_rate'],0,1);number(r['avg_net_return']);number(r['median_net_return'])
            for name in ('random_matched','random'):
                base=raw[name]
                counts(base, ('draws',))
                if base['draws']==0: raise ValueError('empty baseline')
                for metric in ('avg_net_return','hit_rate'):
                    values=base[metric]
                    for key in ('observed','random_mean','difference','random_p2_5','random_p97_5'):
                        number(values[key])
                    number(values['p_value_one_sided'],0,1)
                    if values['random_p2_5'] > values['random_p97_5']:
                        raise ValueError('reversed random draw interval')
                if not isinstance(base['method'],str) or not isinstance(base['pooled'],dict):
                    raise ValueError('missing baseline method')
            if not isinstance(raw['warnings'],list) or not isinstance(raw['data_quality']['known_limitations'],list):
                raise ValueError('missing limitations')
        else:
            raise ValueError('unsupported schema')
