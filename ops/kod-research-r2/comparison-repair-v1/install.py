"""Install the comparison input helper without restarting the collector."""
from pathlib import Path
import hashlib
import json
import os
import pwd
import shutil
import subprocess

source = Path(__file__).resolve().parent
target = Path('/var/lib/kod-research-r2-ops/repairs/comparison-inputs-20261107')
target.mkdir(parents=True, exist_ok=True)
files = ('comparison_inputs.py', 'export_results.py', 'AMENDMENT.md')
for name in files:
    if source/name != target/name:
        shutil.copyfile(source/name, target/name)
    os.chmod(target/name, 0o644)

unit = '''[Unit]
Description=KOD R2 daily inputs for matched comparisons
After=network-online.target kod-research-r2.service
[Service]
Type=oneshot
User=kod
Group=kod
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/usr/bin/python3 -B /var/lib/kod-research-r2-ops/repairs/comparison-inputs-20261107/comparison_inputs.py
ExecStartPost=/usr/bin/python3 -B /var/lib/kod-research-r2-ops/repairs/comparison-inputs-20261107/export_results.py --state /var/lib/kod/research-r2 --out /var/lib/kod/research-r2/comparison-inputs/RESULTS.json
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
NoNewPrivileges=true
ReadWritePaths=/var/lib/kod/research-r2
UMask=0027
'''
timer = '''[Unit]
Description=Refresh KOD R2 comparison inputs and recorded outcomes
[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
OnCalendar=*-*-* 00:05:00 UTC
Persistent=true
Unit=kod-research-r2-comparisons.service
[Install]
WantedBy=timers.target
'''
for suffix, value in [('service',unit),('timer',timer)]:
    Path('/etc/systemd/system/kod-research-r2-comparisons.'+suffix).write_text(value)
folder=Path('/var/lib/kod/research-r2/comparison-inputs')
folder.mkdir(exist_ok=True)
user=pwd.getpwnam('kod');os.chown(folder,user.pw_uid,user.pw_gid)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','kod-research-r2-comparisons.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','kod-research-r2-comparisons.service'],check=True)
print(json.dumps({'installed':True,'collector_restarted':False,
    'files':{name:hashlib.sha256((target/name).read_bytes()).hexdigest() for name in files}}))
