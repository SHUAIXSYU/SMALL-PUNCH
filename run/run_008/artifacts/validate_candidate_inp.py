"""Use the installed Abaqus 2024 input parser only; no Job/solver/datacheck."""
import argparse,json,os
from pathlib import Path
import inpParser
def main():
    p=argparse.ArgumentParser(); p.add_argument('--inp',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    path=Path(a.inp).resolve(); output=Path(a.output).resolve(); os.chdir(str(path.parent)); parsed=inpParser.InputFile(path.name).parse()
    if parsed is None: raise RuntimeError('Abaqus input parser returned no parsed input')
    result={'status':'PASS_ABAQUS_INPUT_PARSE','parser':'Abaqus 2024 inpParser.InputFile.parse','input_relative_path':'run/run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp','input_file':path.name,'parse_return_type':type(parsed).__name__,'solver_started':False,'datacheck_started':False,'job_submitted':False,'scope':'Input syntax parsing only; no model physics/convergence validation.'}
    output.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
