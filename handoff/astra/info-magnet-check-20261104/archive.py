"""Checksum-verified, bounded public Binance hourly archive access.

Construction/import performs no data request. Only explicit metadata or bar calls
contact Binance's public archive. Metadata refusal and download failures are not
missing bars. The caller owns the frozen study window and outcome-read boundary.
"""
from __future__ import annotations

import csv
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

UTC = timezone.utc
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
BASE = 'https://data.binance.vision/'
S3 = 'https://s3-ap-northeast-1.amazonaws.com/data.binance.vision'
NS = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}
SYMBOL = re.compile(r'^[A-Z0-9]{1,30}USDT$')
MONTH = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')
# Exported for explicit caller eligibility, never inferred by substring (JUP is not UP).
STABLE_FIAT_BASES = frozenset({'USDT','USDC','BUSD','TUSD','FDUSD','USDP','PAX','DAI',
    'USDS','USDD','USDE','USD1','RLUSD','EUR','EURI','AEUR','GBP','TRY','BRL','AUD','RUB',
    'UAH','BIDR','IDRT','NGN','VAI','UST','USTC'})


class DownloadError(RuntimeError):
    """Availability unknown: refused, unreachable, or inconsistent public archive."""


class DataError(RuntimeError):
    """Checksum, evidence, or data-format integrity failed."""


def _stamp():
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _epoch(value):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DataError('invalid epoch') from exc
    if not n.is_finite() or n != n.to_integral_value():
        raise DataError('epoch must be a finite integer')
    if Decimal(946684800000) <= n < Decimal(4102444800000):
        micros = int(n) * 1000
        unit = 'ms'
    elif Decimal(946684800000000) <= n < Decimal(4102444800000000):
        micros = int(n)
        unit = 'us'
    else:
        raise DataError('epoch outside 2000–2100 ms/us range')
    return EPOCH + timedelta(microseconds=micros), unit


def _number(value, *, positive=False):
    try:
        n = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise DataError('invalid numeric field') from exc
    if not n.is_finite() or n < 0 or (positive and n <= 0):
        raise DataError('nonfinite or invalid numeric range')
    return n


def decode_zip(raw, symbol, month, archive_sha256=None, *, invalid_hours=None):
    """Pure parser; optional invalid_hours retains only localizable partial hours.

    Default direct use stays strict. Archive.bar never returns an incomplete hour
    as missing: it raises DataError if that explicitly requested hour is invalid.
    """
    name = f'{symbol}-1h-{month}.csv'
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if len(infos) != 1 or infos[0].filename != name:
                raise DataError('archive must contain exactly its expected CSV')
            if infos[0].file_size > 16 * 1024 * 1024:
                raise DataError('uncompressed hourly archive exceeds bound')
            text = archive.read(name).decode('utf-8-sig')
    except (zipfile.BadZipFile, UnicodeDecodeError, KeyError) as exc:
        raise DataError('invalid ZIP or CSV encoding') from exc
    bars = {}
    for row_number, row in enumerate(csv.reader(io.StringIO(text)), 1):
        if not row:
            continue
        if row[0] in ('open_time', 'open_timestamp'):
            if bars:
                raise DataError('CSV header appears after data')
            continue
        if len(row) != 12:
            raise DataError('expected twelve Binance kline columns')
        opened, open_unit = _epoch(row[0])
        closed, close_unit = _epoch(row[6])
        if open_unit != close_unit:
            raise DataError('mixed timestamp units within one bar')
        end = closed + timedelta(microseconds=1000 if close_unit == 'ms' else 1)
        if opened.strftime('%Y-%m') != month:
            raise DataError('bar does not belong to named archive month')
        if opened.minute or opened.second or opened.microsecond or end - opened != timedelta(hours=1):
            # Verified monthly archives sometimes include a short/incomplete
            # hour. Preserve it as unresolved, but do not let an unrelated bad
            # hour invalidate otherwise valid requested hours in that month.
            bucket = opened.replace(minute=0, second=0, microsecond=0)
            if invalid_hours is None or not (bucket <= opened < end <= bucket + timedelta(hours=1)):
                raise DataError('bar is not one completed UTC hour')
            if bucket in bars or bucket in invalid_hours:
                raise DataError('ambiguous duplicate complete/incomplete hour')
            invalid_hours[bucket] = {'reason':'bar is not one completed UTC hour',
                'csv_row':row_number, 'open_time':opened.isoformat(),
                'close_time':closed.isoformat(), 'close_exclusive':end.isoformat(),
                'open_epoch':row[0], 'close_epoch':row[6]}
            continue
        if invalid_hours is not None and opened in invalid_hours:
            raise DataError('ambiguous duplicate complete/incomplete hour')
        values = {k: _number(row[i], positive=True) for k, i in [('open',1),('high',2),('low',3),('close',4)]}
        if values['low'] > min(values['open'], values['close']) or values['high'] < max(values['open'], values['close']) or values['low'] > values['high']:
            raise DataError('inconsistent OHLC range')
        if opened in bars:
            raise DataError('duplicate hourly bar')
        bars[opened] = {'symbol': symbol, 'open_time': opened, 'close_time': closed,
            'close_exclusive': end, **values, 'base_volume': _number(row[5]),
            'quote_volume': _number(row[7]), 'archive_sha256': archive_sha256 or _sha(raw)}
    return bars


class Archive:
    def __init__(self, cache_root, max_workers=8, *, opener=None, max_cache_months=64):
        if not 1 <= max_workers <= 32 or max_cache_months < 1:
            raise ValueError('invalid concurrency/cache bound')
        self.root = Path(cache_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / 'archive_manifest.jsonl'
        self._opener = opener or urllib.request.urlopen
        self._network = threading.BoundedSemaphore(max_workers)
        self._mutex = threading.RLock()
        self._locks = {}
        self._bar_cache = OrderedDict()
        self.max_cache_months = max_cache_months

    def _lock(self, name):
        with self._mutex:
            return self._locks.setdefault(name, threading.RLock())

    def _write(self, path, raw):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + f'.{threading.get_ident()}.tmp')
        temporary.write_bytes(raw)
        temporary.replace(path)

    def _record(self, value):
        with self._mutex:
            with self.manifest_path.open('a', encoding='utf-8') as out:
                out.write(json.dumps(value, sort_keys=True) + '\n')
                out.flush()

    def _get(self, url, role):
        request = urllib.request.Request(url, headers={'User-Agent':'KOD-archive-research/1.0'})
        try:
            with self._network, self._opener(request, timeout=30) as response:
                if getattr(response, 'status', 200) != 200:
                    raise DownloadError(f'public archive HTTP {response.status}')
                raw = response.read(64 * 1024 * 1024 + 1)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError) as exc:
            raise DownloadError(f'{role} availability unknown: {type(exc).__name__}: {exc}') from exc
        if len(raw) > 64 * 1024 * 1024:
            raise DataError('public response exceeds bound')
        return raw, {'kind':role, 'url':url, 'fetched_at':_stamp(), 'bytes':len(raw), 'sha256':_sha(raw)}

    def _listing(self, prefix):
        marker = None
        prefixes, keys, receipts = [], [], []
        while True:
            params = {'delimiter':'/', 'prefix':prefix}
            if marker is not None:
                params['marker'] = marker
            url = S3 + '?' + urllib.parse.urlencode(params)
            raw, receipt = self._get(url, 'archive_metadata')
            raw_path = Path('metadata_raw') / (receipt['sha256'] + '.xml')
            self._write(self.root / raw_path, raw)
            receipt['cache_path'] = raw_path.as_posix()
            try:
                page = ET.fromstring(raw)
            except ET.ParseError as exc:
                raise DataError('invalid archive listing XML') from exc
            if page.tag != '{' + NS['s3'] + '}ListBucketResult':
                raise DataError('unsupported archive listing response')
            page_prefixes = [p.findtext('s3:Prefix', namespaces=NS) for p in page.findall('s3:CommonPrefixes', NS)]
            page_keys = [p.findtext('s3:Key', namespaces=NS) for p in page.findall('s3:Contents', NS)]
            if any(x is None for x in page_prefixes + page_keys):
                raise DataError('invalid archive listing entries')
            prefixes.extend(page_prefixes)
            keys.extend(page_keys)
            receipts.append(receipt)
            self._record(receipt)
            if page.findtext('s3:IsTruncated', namespaces=NS) != 'true':
                return prefixes, keys, receipts
            next_marker = page.findtext('s3:NextMarker', namespaces=NS)
            if not next_marker:
                entries = page_keys + page_prefixes
                if not entries:
                    raise DataError('truncated listing has no continuation')
                next_marker = max(entries)
            if marker is not None and next_marker <= marker:
                raise DataError('archive listing pagination did not advance')
            marker = next_marker

    def _metadata(self, identity, prefix):
        path = self.root / 'metadata' / (identity + '.json')
        with self._lock('metadata:' + identity):
            if path.exists():
                cached = json.loads(path.read_text())
                if cached.get('prefix') != prefix:
                    raise DataError('metadata cache identity mismatch')
                derived_prefixes, derived_keys = [], []
                for receipt in cached['receipts']:
                    relative = Path(receipt['cache_path'])
                    if relative.is_absolute() or '..' in relative.parts or _sha((self.root / relative).read_bytes()) != receipt['sha256']:
                        raise DataError('metadata evidence hash mismatch')
                    try:
                        page = ET.fromstring((self.root / relative).read_bytes())
                        derived_prefixes.extend(p.findtext('s3:Prefix', namespaces=NS) for p in page.findall('s3:CommonPrefixes', NS))
                        derived_keys.extend(p.findtext('s3:Key', namespaces=NS) for p in page.findall('s3:Contents', NS))
                    except ET.ParseError as exc:
                        raise DataError('invalid cached metadata XML') from exc
                if derived_prefixes != cached['prefixes'] or derived_keys != cached['keys']:
                    raise DataError('parsed metadata differs from retained raw evidence')
                return cached['prefixes'], cached['keys']
            prefixes, keys, receipts = self._listing(prefix)
            record = {'prefix':prefix, 'prefixes':prefixes, 'keys':keys, 'receipts':receipts}
            self._write(path, (json.dumps(record, sort_keys=True, indent=2) + '\n').encode())
            return prefixes, keys

    @staticmethod
    def _symbol(symbol):
        if not isinstance(symbol, str) or not SYMBOL.fullmatch(symbol):
            raise ValueError('explicit ASCII uppercase alphanumeric USDT symbol required')
        return symbol

    def historical_symbols(self):
        prefix = 'data/spot/monthly/klines/'
        prefixes, _ = self._metadata('historical_symbols', prefix)
        return sorted({p[len(prefix):].rstrip('/') for p in prefixes
            if p.startswith(prefix) and SYMBOL.fullmatch(p[len(prefix):].rstrip('/'))})

    def months(self, symbol):
        symbol = self._symbol(symbol)
        prefix = f'data/spot/monthly/klines/{symbol}/1h/'
        _, keys = self._metadata('months_' + symbol, prefix)
        beginning = prefix + symbol + '-1h-'
        return {k[len(beginning):-4] for k in keys if k.startswith(beginning) and k.endswith('.zip') and MONTH.fullmatch(k[len(beginning):-4])}

    def _month(self, symbol, month):
        identity = (symbol, month)
        with self._lock('month:' + symbol + ':' + month):
            with self._mutex:
                if identity in self._bar_cache:
                    self._bar_cache.move_to_end(identity)
                    return self._bar_cache[identity]
            name = f'{symbol}-1h-{month}.zip'
            key = f'data/spot/monthly/klines/{symbol}/1h/{name}'
            path = self.root / key
            checksum = path.with_suffix('.zip.CHECKSUM')
            provenance = path.with_suffix('.zip.receipt.json')
            if not (checksum.exists() and provenance.exists()):
                checksum_raw, checksum_receipt = self._get(BASE + key + '.CHECKSUM', 'official_checksum')
                self._write(checksum, checksum_raw)
                self._record(checksum_receipt)
            else:
                checksum_raw = checksum.read_bytes()
                saved = json.loads(provenance.read_text())
                if saved['checksum_url'] != BASE + key + '.CHECKSUM' or saved['checksum_sha256'] != _sha(checksum_raw):
                    raise DataError('checksum evidence provenance mismatch')
            try:
                fields = checksum_raw.decode('ascii').strip().split()
                expected = fields[0]
                if not re.fullmatch(r'[a-fA-F0-9]{64}', expected) or (len(fields) > 1 and fields[1].lstrip('*') != name):
                    raise ValueError('invalid checksum fields')
            except (UnicodeDecodeError, IndexError, ValueError) as exc:
                raise DataError('invalid official archive checksum') from exc
            reused = path.exists()
            if reused:
                raw = path.read_bytes()
            else:
                raw, downloaded = self._get(BASE + key, 'hourly_archive')
            if _sha(raw) != expected.lower():
                raise DataError('hourly archive differs from official checksum')
            # Persist checksum-verified originals before semantic parsing so a
            # schema/row failure does not discard the evidence needed to audit it.
            if not reused:
                self._write(path, raw)
            record = {'kind':'verified_raw_archive', 'url':BASE + key, 'verified_at':_stamp(),
                'sha256':expected.lower(), 'bytes':len(raw), 'cache_path':key, 'reused_file':reused,
                'checksum_url':BASE + key + '.CHECKSUM', 'checksum_sha256':_sha(checksum_raw),
                'parse_status':'NOT_PARSED_YET'}
            if not reused:
                record['fetched_at'] = downloaded['fetched_at']
            self._write(provenance, (json.dumps(record, sort_keys=True, indent=2) + '\n').encode())
            self._record(dict(record))
            invalid_hours = {}
            try:
                bars = decode_zip(raw, symbol, month, expected.lower(), invalid_hours=invalid_hours)
            except DataError as exc:
                record.update(kind='archive_parse_error', parse_status='ERROR', parse_error=str(exc))
                self._write(provenance, (json.dumps(record, sort_keys=True, indent=2) + '\n').encode())
                self._record(record)
                raise
            record.update(kind='verified_hourly_archive', parse_status='PARSED',
                invalid_hour_diagnostics=[dict(hour=hour.isoformat(), **detail) for hour,detail in sorted(invalid_hours.items())])
            self._write(provenance, (json.dumps(record, sort_keys=True, indent=2) + '\n').encode())
            self._record(record)
            result = (bars, invalid_hours)
            with self._mutex:
                self._bar_cache[identity] = result
                while len(self._bar_cache) > self.max_cache_months:
                    self._bar_cache.popitem(last=False)
            return result

    def bar(self, symbol, hourUTC):
        symbol = self._symbol(symbol)
        if not isinstance(hourUTC, datetime) or hourUTC.utcoffset() is None:
            raise ValueError('timezone-aware UTC hour required')
        hour = hourUTC.astimezone(UTC)
        if hour.minute or hour.second or hour.microsecond:
            raise ValueError('exact UTC hour required')
        if hour + timedelta(hours=1) > datetime.now(UTC):
            raise ValueError('requested hour is not complete yet')
        month = hour.strftime('%Y-%m')
        if month not in self.months(symbol):
            return None
        bars, invalid_hours = self._month(symbol, month)
        if hour in invalid_hours:
            raise DataError('requested hour is incomplete in verified archive: ' + json.dumps(invalid_hours[hour], sort_keys=True))
        return bars.get(hour)
