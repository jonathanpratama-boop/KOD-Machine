# Portable copy: only the fixture-root path differs from original independent reproducer.
import ast,json
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parent
source=ast.parse((root/'run_t6.py').read_text())
# Only pure reviewed simulation functions. Never import lib, strategy, or market data.
safe_nodes=[n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in ('simulate','parametric')]
scope={'np':np,'rng':np.random.default_rng(20261101),'N_PATHS':20000,'DAYS':365}
exec(compile(ast.Module(body=safe_nodes,type_ignores=[]),'pure_run_t6_functions','exec'),scope)
base=scope['simulate']
diagnostics={}
def observed(r):
    eq=np.cumprod(1+r,axis=1)
    old_peak=np.maximum.accumulate(eq,axis=1)
    peak=np.maximum(old_peak,1.0)
    with np.errstate(invalid='ignore'):
        dd_old=eq/old_peak-1
    dd=eq/peak-1
    hit=(eq>=10).any(axis=1)
    ruin=(dd<=-.5).any(axis=1)
    ruin_old=(dd_old<=-.5).any(axis=1)
    t_hit=np.where(hit,np.argmax(eq>=10,axis=1),366)
    t_ruin=np.where(ruin,np.argmax(dd<=-.5,axis=1),366)
    diagnostics[len(diagnostics)]={
        'P_hit10_noDD50_whole_year':round(float((hit & ~ruin).mean()),4),
        'P_terminal10':round(float((eq[:,-1]>=10).mean()),4),
        'P_DD50_corrected_initial1':round(float(ruin.mean()),4),
        'P_hit10_beforeDD50_corrected_initial1':round(float((hit & (t_hit<t_ruin)).mean()),4),
        'paths_dd_reclassified':int((ruin & ~ruin_old).sum())}
    return base(r)
scope['simulate']=observed
res=scope['parametric']()
committed=json.loads((root/'results_t6.json').read_text())['parametric']
report={'all_25_parametric_cells_match_committed_rounded_values':res==committed,'mismatches':{k:{'reproduction':v,'committed':committed[k]} for k,v in res.items() if v!=committed[k]},'selected':{k:{'reported':res[k],'diagnostics':diagnostics[i]} for i,k in enumerate(res) if k in ('Sharpe3.0|vol20%|lev5x','Sharpe1.0|vol20%|lev10x')},'synthetic_first_loss_60pct':base(np.array([[-.6,0.,0.]])),'synthetic_10x_then_half':base(np.array([[9.,-.5,0.]]))}
(root/'synthetic_check_results.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
