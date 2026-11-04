import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

from events_stats import extract_tickers, notice_time, parse_archive, summarize_paired


def notice(identity=1, title='테스트(AAA) KRW 마켓 디지털 자산 추가', at='2026-01-02T12:30:00+09:00'):
    return {'id': identity, 'title': title, 'first_listed_at': at, 'listed_at': '2026-01-02T13:00:00+09:00'}


def page(notices, pages=1, count=None):
    return {'success': True, 'data': {'notices': notices, 'total_pages': pages, 'total_count': len(notices) if count is None else count}}


class NoticeParser(unittest.TestCase):
    def write(self, root, folder, number, value):
        target = Path(root)/folder/f'page_{number}.json'; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False))

    def test_tickers_exclude_markets_dates_and_allow_numeric_prefix(self):
        self.assertEqual(extract_tickers('토큰(1INCH), 코인(ABC) (KRW, BTC, USDT 마켓) (11/30 15:00)'), ['1INCH','ABC'])
        self.assertEqual(extract_tickers('비트코인(BTC) (USDT)'), [])

    def test_first_listed_kst_not_later_revision_and_strict_next_hour(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root,'upbit',1,page([notice(at='2026-01-02T12:00:00+09:00')]))
            result=parse_archive(root); event=result['events'][0]
            self.assertEqual(event['notice_at'],'2026-01-02T03:00:00Z')
            self.assertEqual(event['entry_at'],'2026-01-02T04:00:00Z')
            self.assertTrue(event['eligible_primary']); self.assertFalse(result['prices_read'])
        self.assertEqual(notice_time('2026-01-02T12:30:00').hour,3)

    def test_exact_family_only_and_alt_market_is_descriptive(self):
        with tempfile.TemporaryDirectory() as root:
            values=[notice(1),notice(2,'코인(BBB) BTC, USDT 마켓 디지털 자산 추가'),
                    notice(3,'코인(CCC) 신규 거래지원 안내 (KRW, BTC, USDT 마켓)'),
                    notice(4,'코인 KRW 마켓 디지털 자산 추가')]
            self.write(root,'upbit',1,page(values))
            result=parse_archive(root)
            self.assertEqual(result['event_count'],2); self.assertEqual(result['primary_krw_events'],1)
            self.assertFalse(result['events'][1]['eligible_primary'])
            self.assertEqual({r['reason'] for r in result['rejected_notices']},{'OUTSIDE_FROZEN_TITLE_FAMILY','NO_UNAMBIGUOUS_TICKER'})

    def test_invalid_original_uses_repair_but_valid_original_remains(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root,'upbit',1,page([notice(1)],pages=2,count=2))
            path=Path(root)/'upbit/page_2.json'; path.write_text('error code: 1015')
            self.write(root,'upbit_redownload',2,page([notice(2,'코인(BBB) KRW 마켓 디지털 자산 추가')],pages=2,count=2))
            self.write(root,'upbit_redownload',1,page([notice(1,'수정(AAA) KRW 마켓 디지털 자산 추가')],pages=2,count=2))
            result=parse_archive(root)
            self.assertEqual(result['event_count'],2); self.assertEqual(result['missing_pages'],[])
            self.assertFalse(result['pages'][0]['fallback_used']); self.assertTrue(result['pages'][1]['fallback_used'])
            first=next(e for e in result['events'] if e['notice_id']==1)
            self.assertEqual(first['title'],notice()['title'])
            self.assertIn('CONFLICTING_NOTICE_REVISIONS',first['review_required'])
            self.assertEqual(first['notice_revision_count'],2)

    def test_duplicate_notice_ticker_dedup_and_missing_pages_visible(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root,'upbit',1,page([notice(1),notice(1)],pages=2,count=3))
            result=parse_archive(root)
            self.assertEqual(result['event_count'],1); self.assertEqual(result['duplicate_event_occurrences'],1)
            self.assertEqual(result['missing_pages'],[2])

    def test_bad_timestamp_kept_as_rejection(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root,'upbit',1,page([notice(at='not-a-date')]))
            self.assertEqual(parse_archive(root)['rejected_notices'][0]['reason'],'INVALID_FIRST_LISTED_AT')


class PairedStats(unittest.TestCase):
    def rows(self,n=30,gross=.10,controls=.01,same_date=False):
        return [{'event_id':str(i),'notice_at':('2026-01-01T00:00:00Z' if same_date else (dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(days=i)).isoformat()),
                 'event_gross_return':gross,'control_gross_returns':[controls]*5} for i in range(n)]

    def test_fixed_costs_positive_gate_and_reproducibility(self):
        first=summarize_paired(self.rows(),bootstrap_reps=250)
        self.assertEqual(first,summarize_paired(self.rows(),bootstrap_reps=250))
        self.assertAlmostEqual(first['owner_cost']['mean_paired_net_excess'],.07)
        self.assertAlmostEqual(first['original_cost']['mean_paired_net_excess'],.084)
        self.assertTrue(first['pass_gate']); self.assertEqual(first['n'],30)

    def test_negative_owner_cost_kills_even_if_lower_cost_positive(self):
        value=summarize_paired(self.rows(gross=.015,controls=0),bootstrap_reps=200)
        self.assertGreater(value['original_cost']['mean_event_net_return'],0)
        self.assertLess(value['owner_cost']['mean_event_net_return'],0)
        self.assertFalse(value['pass_gate'])

    def test_missing_and_invalid_outcomes_block_gate(self):
        rows=self.rows(); rows[-1]['control_gross_returns']=[0.01]*4
        value=summarize_paired(rows,expected_primary_count=30,bootstrap_reps=100)
        self.assertEqual(value['n'],29); self.assertEqual(value['unresolved_primary'],1)
        self.assertFalse(value['pass_gate'])
        value=summarize_paired(self.rows(),expected_primary_count=31,bootstrap_reps=100)
        self.assertEqual(value['unresolved_primary'],1); self.assertFalse(value['pass_gate'])

    def test_one_notice_date_cannot_give_valid_cluster_interval(self):
        value=summarize_paired(self.rows(same_date=True),bootstrap_reps=200)
        self.assertEqual(value['utc_notice_date_clusters'],1)
        self.assertEqual(value['owner_cost']['paired_net_excess_95_ci'],[None,None])
        self.assertFalse(value['pass_gate'])

    def test_cluster_estimator_is_event_weighted_not_date_mean(self):
        rows=self.rows(n=3)
        rows[0]['notice_at']=rows[1]['notice_at']='2026-01-01T00:00:00Z'
        rows[0]['event_gross_return']=rows[1]['event_gross_return']=.30
        rows[2]['event_gross_return']=0
        value=summarize_paired(rows,bootstrap_reps=100)
        self.assertAlmostEqual(value['mean_event_gross_return'],.20)
        self.assertEqual(value['utc_notice_date_clusters'],2)
        self.assertFalse(value['pass_gate'])

    def test_duplicate_and_nonfinite_rows_are_unresolved(self):
        rows=self.rows(); rows[1]['event_id']=rows[0]['event_id']; rows[2]['event_gross_return']=float('nan')
        value=summarize_paired(rows,bootstrap_reps=100)
        self.assertEqual(value['n'],28); self.assertEqual(len(value['invalid_rows']),2)
        self.assertFalse(value['pass_gate'])

if __name__=='__main__': unittest.main()
