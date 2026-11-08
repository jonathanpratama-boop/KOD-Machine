"""Download the exact externally licensed model revisions in protocol.json."""
import argparse
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', type=Path, required=True)
    args = parser.parse_args()
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
        (folder / 'revision.json').write_text(json.dumps(revision))
        print(name, revision['sha'])


if __name__ == '__main__':
    main()
