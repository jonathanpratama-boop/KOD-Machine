"""Stream a complete oversized ledger transaction without changing research.

Ordinary chunks use the frozen exporter byte for byte. Only its exact known
oversized-transaction exception invokes this fallback; that exporter raised
before it could publish this range. The existing cursor remains transactional.
"""
import gzip
import hashlib
import os
from pathlib import Path
import tempfile

OVERSIZE = 'ledger transaction exceeds bounded export; preserve local DB and report'
BOUNDARIES = ('PROTOCOL', 'SOURCE_PACKET', 'RESEARCH_CHECKPOINT')


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def stream_next_boundary(engine, directory, canonical):
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    with engine.transaction(engine):
        after = engine.get('export_seq', 0)
        boundary = engine.db.execute(
            "SELECT seq FROM ledger WHERE seq>? AND kind IN (?,?,?) ORDER BY seq LIMIT 1",
            (after, *BOUNDARIES),
        ).fetchone()
        if boundary is None:
            raise ValueError(OVERSIZE)
        end = boundary[0]
        descriptor, temporary_name = tempfile.mkstemp(prefix='.ledger-', suffix='.tmp', dir=destination)
        temporary = Path(temporary_name)
        count, first, tip = 0, None, None
        try:
            with os.fdopen(descriptor, 'wb') as stream:
                with gzip.GzipFile(fileobj=stream, mode='wb', filename='', compresslevel=6, mtime=0) as packed:
                    for record in engine.db.execute(
                        'SELECT * FROM ledger WHERE seq>? AND seq<=? ORDER BY seq', (after, end)
                    ):
                        row = dict(record)
                        if row['seq'] != after + count + 1:
                            raise ValueError('ledger sequence gap during export')
                        packed.write((canonical(row) + '\n').encode())
                        first = row['seq'] if first is None else first
                        tip = row['hash']
                        count += 1
                stream.flush()
                os.fsync(stream.fileno())
            if count == 0 or first + count - 1 != end:
                raise ValueError('incomplete ledger transaction during export')
            sha = file_hash(temporary)
            path = destination / f'ledger-{first:010d}-{end:010d}-{sha}.jsonl.gz'
            if path.exists():
                if file_hash(path) != sha:
                    raise ValueError('immutable ledger export changed')
            else:
                os.replace(temporary, path)
            descriptor = os.open(destination, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            engine.set('export_seq', end)
            return {'records': count, 'last_seq': end, 'file': str(path), 'sha256': sha,
                    'ledger_tip': tip, 'cache_backup_required': False}
        finally:
            temporary.unlink(missing_ok=True)


def install(engine_module):
    original = engine_module.ResearchEngine.export_incremental

    def export_incremental(self, directory, limit=5000):
        try:
            return original(self, directory, limit=limit)
        except ValueError as error:
            if str(error) != OVERSIZE:
                raise
        return stream_next_boundary(self, directory, engine_module.canonical)

    engine_module.ResearchEngine.export_incremental = export_incremental
    return export_incremental
