import os
from pathlib import Path
import subprocess
import yaml

ROOT=Path(__file__).parents[1]
WORKFLOW=yaml.safe_load((ROOT/'.github/workflows/static-release.yml').read_text())
SELECTED='core/ConfigMap/toolhive-system/ops-mcp-server-code'
CONTRACT='contracts/agent-runtime-domain-toolhive-system.yaml'

def test_validate_rejects_unreviewed_or_disabled_exact_selection():
    script=next(s['run'] for s in WORKFLOW['jobs']['validate']['steps'] if s.get('name')=='Validate exact force selection')
    for selected,enabled,ok in [(SELECTED,'true',True),(SELECTED,'false',False),('core/Secret/toolhive-system/private','true',False)]:
        result=subprocess.run(['bash','-c',script],cwd=ROOT,env={**os.environ,'CONTRACT':CONTRACT,'FORCE_TAKEOVER':enabled,'REVIEWED_FORCE_OBJECT':selected},capture_output=True,text=True)
        assert (result.returncode==0)==ok

def test_both_native_operation_paths_pass_only_the_selected_object():
    count=0
    for job in WORKFLOW['jobs'].values():
        for step in job.get('steps',[]):
            text=step.get('run','')
            if 'for value in ([selected] if selected else allowed)' not in text:continue
            code=text.split('import os,sys,yaml\n',1)[1].split('\nPY\n',1)[0]
            result=subprocess.run(['python3','-',CONTRACT],input='import os,sys,yaml\n'+code,cwd=ROOT,env={**os.environ,'REVIEWED_FORCE_OBJECT':SELECTED},capture_output=True,text=True,check=True)
            assert result.stdout.splitlines()==[SELECTED]
            count+=1
    assert count==2
