"""Existing FE arithmetic and figure reproduction only; no Abaqus call."""
from pathlib import Path
from analyze_h4 import analyze
from boundary_diagnostic import boundary
from plot_h4 import figures
if __name__=='__main__':
 root=Path(__file__).resolve().parent;out=root/'reproduced';analyze(root,out);boundary(root,out);figures(root,out,out/'figures')
