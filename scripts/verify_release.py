"""Verify an explicit public release manifest; refresh only its existing allowlist."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
SLUG='echomuse_household_voice'
BASE='ghcr.io/wilbowes/echomuse-controller@sha256:4f21aec35044644d9cec0ed15f941904f6232478d69665b8871031a9b97a6056'
MODULES={'em_controller.py','em_api.py','em_esphome.py','em_household_audio.py'}


def verify(root=ROOT,*,refresh=False,tag=None):
    root=Path(root)
    manifest=json.loads((root/'PUBLIC-RELEASE-MANIFEST.json').read_text())
    allowed=set(manifest['files'])
    if any(Path(name).is_absolute() or '..' in Path(name).parts or '\\' in name for name in allowed):
        raise ValueError('Invalid manifest path')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()
        and not any(part in ('.git','__pycache__','.venv','.pytest_cache','dist') for part in p.relative_to(root).parts)}
    if actual!=allowed|{'PUBLIC-RELEASE-MANIFEST.json'}:raise ValueError('Release file allowlist changed')
    hashes={}
    for name in sorted(allowed):
        path=root/name
        if path.is_symlink() or root.resolve() not in path.resolve().parents:raise ValueError('Unsafe release path')
        raw=path.read_bytes();text=raw.decode('utf-8')
        if b'\r\n' in raw:raise ValueError('Release files require LF line endings')
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}',text):
            raise ValueError('Potential credential in '+name)
        if name.endswith('.py'):ast.parse(text,filename=name)
        hashes[name]=hashlib.sha256(raw).hexdigest()
    config=json.loads((root/SLUG/'config.json').read_text())
    pin=json.loads((root/'upstream-pin.json').read_text())
    docker=(root/SLUG/'Dockerfile').read_text()
    if pin['base_image']!=BASE or not docker.startswith('FROM '+BASE+'\n'):raise ValueError('Public base pin mismatch')
    if config['arch']!=['amd64'] or config['slug']!=SLUG or config['boot']!='manual':raise ValueError('Architecture or migration boundary changed')
    if not config['host_network'] or config['docker_api'] or config['hassio_api'] or config['homeassistant_api'] or config['full_access']:raise ValueError('App privilege contract changed')
    if config['options']['external_audio_enabled'] is not False or config['options']['external_audio_devices']!=[]:raise ValueError('Private provisioning must not be a default')
    if set(pin['patched_input_sha256'])!=MODULES:raise ValueError('Controller module scope changed')
    if tag is not None and tag!='v'+config['version']:raise ValueError('Git tag must match Supervisor image version')
    if f"ARG BUILD_VERSION={config['version']}\n" not in docker:raise ValueError('Docker and add-on versions differ')
    if config['image']!=manifest['image_repository']:raise ValueError('Image repository changed')
    if refresh:
        manifest['version']=config['version'];manifest['files']=hashes
        (root/'PUBLIC-RELEASE-MANIFEST.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    elif hashes!=manifest['files'] or config['version']!=manifest['version']:
        raise ValueError('Reviewed release hashes or version changed')
    return {'version':config['version'],'image':config['image'],'files':len(hashes),'verified':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh',action='store_true',help='Update hashes of existing allowlisted files after review')
    parser.add_argument('--tag')
    args=parser.parse_args()
    print(json.dumps(verify(refresh=args.refresh,tag=args.tag)))
