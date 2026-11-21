"""Offline arithmetic/figures only. No Abaqus, training or network calls."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'code'))
from analyze_holdout import analyze
from analyze_robustness import robustness
from plot_holdout import figures
out=root/'reproduced'
analyze(root/'data',out)
robustness(root/'data',out)
figures(root/'data',out,out/'figures')
print('Finished offline reproduction; no solver or new parameter fitting')
