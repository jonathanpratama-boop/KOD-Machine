"""Download the exact externally licensed model revisions in protocol.json."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', type=Path, required=True)
    args = parser.parse_args()
    artifacts = json.loads((HERE / 'MODEL_ARTIFACTS.json').read_text())
    for name, revision in json.loads((HERE / 'protocol.json').read_text())['models'].items():
        folder = args.models / name
        folder.mkdir(parents=True, exist_ok=True)
        for filename in ['config.json', 'model.safetensors']:
            destination = folder / filename
            url = f"https://huggingface.co/{revision['repo']}/resolve/{revision['sha']}/{filename}"
            if not destination.exists():
                temporary = destination.with_suffix(destination.suffix + '.download')
                urllib.request.urlretrieve(url, temporary)
                temporary.rename(destination)
            key = 'weights_sha256' if filename == 'model.safetensors' else 'config_sha256'
            if hashlib.sha256(destination.read_bytes()).hexdigest() != artifacts[name][key]:
                raise ValueError(f'{name}/{filename} differs from the pinned artifact; refusing to relabel it')
        (folder / 'revision.json').write_text(json.dumps(revision))
        print(name, revision['sha'])


if __name__ == '__main__':
    main()
