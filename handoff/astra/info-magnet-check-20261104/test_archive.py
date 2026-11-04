import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import zipfile
from concurrent.futures import ThreadPoolExecutor

from archive import Archive, BASE, S3, DataError, DownloadError, decode_zip

UTC = timezone.utc
HOUR = datetime(2025, 1, 2, tzinfo=UTC)


def epoch(at, unit='ms'):
    micros = int((at - datetime(1970, 1, 1, tzinfo=UTC)).total_seconds() * 1000000)
    return str(micros // 1000 if unit == 'ms' else micros)


def row(at=HOUR, unit='ms'):
    end = at + timedelta(hours=1) - timedelta(microseconds=1000 if unit == 'ms' else 1)
    return [epoch(at, unit), '10', '12', '9', '11', '100', epoch(end, unit), '1050', '4', '50', '525', '0']


def zipped(rows, name='JUPUSDT-1h-2025-01.csv'):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerows(rows)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, out.getvalue())
    return buffer.getvalue()


def listing(prefixes=(), keys=(), truncated=False, marker=None):
    lines = ['<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">', '<IsTruncated>'+str(truncated).lower()+'</IsTruncated>']
    lines += ['<CommonPrefixes><Prefix>'+p+'</Prefix></CommonPrefixes>' for p in prefixes]
    lines += ['<Contents><Key>'+k+'</Key></Contents>' for k in keys]
    if marker:
        lines.append('<NextMarker>'+marker+'</NextMarker>')
    return ('\n'.join(lines)+'</ListBucketResult>').encode()


class Response:
    status = 200
    def __init__(self, raw): self.raw = raw
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, n): return self.raw[:n]


class ArchiveTests(unittest.TestCase):
    def test_ms_us_per_row_normalization(self):
        data = decode_zip(zipped([row(), row(HOUR+timedelta(hours=1), 'us')]), 'JUPUSDT','2025-01')
        self.assertEqual(len(data), 2)
        for h in (HOUR, HOUR+timedelta(hours=1)):
            self.assertEqual(data[h]['open_time'], h)
            self.assertEqual(data[h]['close_exclusive'], h+timedelta(hours=1))
            self.assertEqual(str(data[h]['open']), '10')

    def test_corrupt_and_incomplete_rows_rejected(self):
        bad = row(); bad[6] = epoch(HOUR+timedelta(minutes=30))
        for rows in [[bad], [row(),row()], [row()[:8]]]:
            with self.assertRaises(DataError): decode_zip(zipped(rows), 'JUPUSDT', '2025-01')
        bad = row(); bad[2] = 'NaN'
        with self.assertRaises(DataError): decode_zip(zipped([bad]), 'JUPUSDT', '2025-01')

    def test_s3_pagination_keeps_jup_and_delisted_names(self):
        calls=[]
        prefix='data/spot/monthly/klines/'
        def opener(request, **kw):
            calls.append(request.full_url)
            params=urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)
            if 'marker' not in params:
                return Response(listing([prefix+'BTCUSDT/'],truncated=True,marker=prefix+'BTCUSDT/'))
            return Response(listing([prefix+'JUPUSDT/',prefix+'OLDUSDT/',prefix+'ÜUSDT/',prefix+'BTCBUSD/']))
        with tempfile.TemporaryDirectory() as tmp:
            a=Archive(tmp,opener=opener)
            self.assertEqual(a.historical_symbols(), ['BTCUSDT','JUPUSDT','OLDUSDT'])
            self.assertEqual(a.historical_symbols(), ['BTCUSDT','JUPUSDT','OLDUSDT'])
            self.assertEqual(len(calls),2)
            entries=[json.loads(line) for line in a.manifest_path.read_text().splitlines()]
            self.assertEqual(len(entries),2)
            self.assertTrue(all(e['fetched_at'] and e['sha256'] for e in entries))

    def fixture(self, tmp, *, bad_checksum=False, missing=False, fail=False, rows=None):
        data=zipped([row()] if rows is None else rows); calls=[]
        key='data/spot/monthly/klines/JUPUSDT/1h/JUPUSDT-1h-2025-01.zip'
        def opener(request, **kw):
            url=request.full_url; calls.append(url)
            if fail: raise urllib.error.URLError('fixture failure')
            if url.startswith(S3): return Response(listing(keys=[] if missing else [key]))
            if url.endswith('.CHECKSUM'):
                checksum=('0'*64 if bad_checksum else hashlib.sha256(data).hexdigest())
                return Response((checksum+'  JUPUSDT-1h-2025-01.zip\n').encode())
            self.assertEqual(url, BASE+key)
            return Response(data)
        return Archive(tmp, opener=opener), calls

    def test_verified_bar_and_known_missing_hour(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,calls=self.fixture(tmp)
            bar=a.bar('JUPUSDT',HOUR)
            self.assertEqual(str(bar['close']),'11')
            self.assertIsNone(a.bar('JUPUSDT',HOUR+timedelta(hours=1)))
            self.assertEqual(len(calls),3)
            # A fresh Archive must verify cached evidence, with no extra request.
            again=Archive(tmp,opener=lambda *a,**k: self.fail('unexpected request'))
            self.assertEqual(again.bar('JUPUSDT',HOUR)['close'],bar['close'])

    def test_known_month_missing_is_none_not_network_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,calls=self.fixture(tmp,missing=True)
            self.assertIsNone(a.bar('JUPUSDT',HOUR)); self.assertEqual(len(calls),1)
        with tempfile.TemporaryDirectory() as tmp:
            a,calls=self.fixture(tmp,fail=True)
            with self.assertRaises(DownloadError): a.bar('JUPUSDT',HOUR)

    def test_bad_official_checksum_is_integrity_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,calls=self.fixture(tmp,bad_checksum=True)
            with self.assertRaises(DataError): a.bar('JUPUSDT',HOUR)

    def test_parallel_same_month_downloads_once_and_manifest_is_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,calls=self.fixture(tmp)
            with ThreadPoolExecutor(8) as pool:
                results=list(pool.map(lambda _:a.bar('JUPUSDT',HOUR),range(20)))
            self.assertEqual(len(calls),3)
            self.assertEqual(len(results),20)
            entries=[json.loads(line) for line in a.manifest_path.read_text().splitlines()]
            self.assertEqual(len(entries),4)
            self.assertEqual(entries[-1]['kind'],'verified_hourly_archive')

    def test_cached_metadata_values_cannot_diverge_from_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,calls=self.fixture(tmp)
            a.months('JUPUSDT')
            path=Path(tmp)/'metadata/months_JUPUSDT.json'
            obj=json.loads(path.read_text()); obj['keys']=[]; path.write_text(json.dumps(obj))
            with self.assertRaises(DataError): a.months('JUPUSDT')

    def test_ambiguous_time_and_unsafe_symbol_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Archive(tmp,opener=lambda *a,**k:self.fail('unexpected request'))
            with self.assertRaises(ValueError): a.bar('../JUPUSDT',HOUR)
            with self.assertRaises(ValueError): a.bar('JUPUSDT',HOUR.replace(tzinfo=None))
            with self.assertRaises(ValueError): a.bar('JUPUSDT',HOUR+timedelta(minutes=1))

    def test_unrelated_short_hour_preserved_and_requested_short_hour_is_error(self):
        bad = row(HOUR+timedelta(hours=2))
        bad[6] = epoch(HOUR+timedelta(hours=3)-timedelta(milliseconds=1334))
        with tempfile.TemporaryDirectory() as tmp:
            a,calls=self.fixture(tmp,rows=[row(),bad])
            self.assertEqual(str(a.bar('JUPUSDT',HOUR)['close']),'11')
            self.assertIsNone(a.bar('JUPUSDT',HOUR+timedelta(hours=1)))
            with self.assertRaisesRegex(DataError,'requested hour is incomplete'):
                a.bar('JUPUSDT',HOUR+timedelta(hours=2))
            provenance=next(Path(tmp).rglob('*.zip.receipt.json'))
            info=json.loads(provenance.read_text())
            self.assertEqual(len(info['invalid_hour_diagnostics']),1)
            self.assertEqual(info['invalid_hour_diagnostics'][0]['csv_row'],2)
            self.assertTrue(next(Path(tmp).rglob('*.zip')).exists())

    def test_partial_listing_hour_is_error_not_missing_but_next_hour_usable(self):
        partial=row(HOUR+timedelta(minutes=5))
        partial[6]=epoch(HOUR+timedelta(hours=1)-timedelta(milliseconds=1))
        with tempfile.TemporaryDirectory() as tmp:
            a,calls=self.fixture(tmp,rows=[partial,row(HOUR+timedelta(hours=1))])
            with self.assertRaisesRegex(DataError,'requested hour is incomplete'):
                a.bar('JUPUSDT',HOUR)
            self.assertEqual(a.bar('JUPUSDT',HOUR+timedelta(hours=1))['open_time'],HOUR+timedelta(hours=1))

    def test_verified_raw_and_receipt_preserved_on_nonlocalized_parse_failure(self):
        bad=row();bad[2]='NaN'
        with tempfile.TemporaryDirectory() as tmp:
            a,calls=self.fixture(tmp,rows=[bad])
            with self.assertRaises(DataError): a.bar('JUPUSDT',HOUR)
            self.assertEqual(len(list(Path(tmp).rglob('*.zip'))),1)
            receipt=json.loads(next(Path(tmp).rglob('*.zip.receipt.json')).read_text())
            self.assertEqual(receipt['parse_status'],'ERROR')
            raw=next(Path(tmp).rglob('*.zip')).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),receipt['sha256'])

    def test_ambiguous_multiple_rows_for_one_hour_not_silently_resolved(self):
        partial=row(HOUR+timedelta(minutes=5))
        partial[6]=epoch(HOUR+timedelta(hours=1)-timedelta(milliseconds=1))
        with tempfile.TemporaryDirectory() as tmp:
            a,calls=self.fixture(tmp,rows=[partial,row()])
            with self.assertRaisesRegex(DataError,'ambiguous duplicate'):
                a.bar('JUPUSDT',HOUR)


if __name__ == '__main__': unittest.main()
