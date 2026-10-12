"""Static INP/JNL/log audit. Never executes or replays Journal code."""
import ast
from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'run/run_005/artifacts/private'

def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def blocks(path):
    result = []
    current = None
    part = instance = step = None
    for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('**'):
            continue
        if line.startswith('*'):
            bits = [b.strip() for b in line[1:].split(',')]
            keyword = bits[0].lower()
            opts = {}
            for bit in bits[1:]:
                key, sep, val = bit.partition('=')
                opts[key.lower()] = val if sep else True
            if keyword == 'part': part = opts['name']
            if keyword == 'instance': instance = opts['name']
            if keyword == 'step': step = opts.get('name')
            current = dict(keyword=keyword, options=opts, line=number, part=part, instance=instance, step=step, rows=[])
            result.append(current)
            if keyword == 'end part': part = None
            if keyword == 'end instance': instance = None
            if keyword == 'end step': step = None
        elif current is not None:
            current['rows'].append(dict(line=number, text=line))
    return result

def expanded(block):
    vals = []
    for row in block['rows']:
        nums = [int(s) for s in row['text'].split(',') if s.strip()]
        if 'generate' in block['options']:
            vals.extend(range(nums[0], nums[1]+1, nums[2] if len(nums)>2 else 1))
        else: vals.extend(nums)
    return vals

def main():
    inventory = json.loads((OUT / 'file_inventory.json').read_text(encoding='utf-8'))
    selected = ROOT / inventory['selected_group']
    inp = next(selected.glob('*.inp'))
    journal = next(selected.glob('*.jnl'))
    inp_blocks = blocks(inp)
    dump('inp_blocks.json', inp_blocks)
    node_blocks = [b for b in inp_blocks if b['keyword'] == 'node' and b['part'] == 'part_specimen']
    nodes = {int(p[0]): [float(v) for v in p[1:]] for b in node_blocks for row in b['rows'] for p in [[s.strip() for s in row['text'].split(',') if s.strip()]]}
    elements = {int(p[0]): [int(v) for v in p[1:]] for b in inp_blocks if b['keyword'] == 'element' for row in b['rows'] for p in [[s.strip() for s in row['text'].split(',') if s.strip()]]}
    nsets = {b['options']['nset']: expanded(b) for b in inp_blocks if b['keyword']=='nset' and b['part']=='part_specimen'}
    elsets = {b['options']['elset']: expanded(b) for b in inp_blocks if b['keyword']=='elset' and b['part']=='part_specimen'}
    surfaces = {}
    edges = {'S1':(0,1),'S2':(1,2),'S3':(2,3),'S4':(3,0)}
    for b in inp_blocks:
        if b['keyword']=='surface' and b['part']=='part_specimen':
            segs=[]
            for row in b['rows']:
                name, side = [x.strip() for x in row['text'].split(',')][:2]
                for e in elsets[name]:
                    conn=elements[e]
                    pair=[conn[i] for i in edges[side.upper()]]
                    segs.append(dict(element=e,side=side,nodes=pair,coordinates=[nodes[n] for n in pair]))
            surfaces[b['options']['name']]=segs
    plastic = next(b for b in inp_blocks if b['keyword']=='plastic')
    table = [[float(v) for v in row['text'].split(',') if v.strip()] for row in plastic['rows']]
    static = dict(node_count=len(nodes), element_count=len(elements),
        specimen_bounds=[[min(x[i] for x in nodes.values()),max(x[i] for x in nodes.values())] for i in range(2)],
        node_sets={k:dict(count=len(v),bounds=[[min(nodes[n][i] for n in v),max(nodes[n][i] for n in v)] for i in range(2)]) for k,v in nsets.items()},
        surfaces=surfaces, plastic=dict(count=len(table),first=table[0],last=table[-1],
            increasing_strain=all(b[1]>a[1] for a,b in zip(table,table[1:])),nondecreasing_stress=all(b[0]>=a[0] for a,b in zip(table,table[1:])),
            semantics='UNKNOWN: numeric format does not prove true stress/equivalent plastic strain provenance'),
        relevant_blocks=[b for b in inp_blocks if b['keyword'] not in ['node','element','nset','elset','plastic']])
    dump('inp_model.json',static)
    text = journal.read_text(encoding='mbcs')
    parsed=ast.parse(text)
    operations=[]
    messages=[]
    tables=[]
    for statement in parsed.body:
        segment=ast.get_source_segment(text,statement)
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            call=statement.value
            name=ast.unparse(call.func)
            if name.endswith('._Message'):
                if call.args and isinstance(call.args[0], ast.Name) and call.args[0].id in ['JOB_COMPLETED','ABORTED','ERROR','STARTED']:
                    messages.append(dict(line=statement.lineno,code=segment))
                continue
            if name.endswith('.Plastic'):
                table_node=next(k.value for k in call.keywords if k.arg=='table')
                jt=ast.literal_eval(table_node)
                tables.append(dict(line=statement.lineno,rows=jt))
                segment=name+'(table=<'+str(len(jt))+' rows; separately retained>)'
        operations.append(dict(line=statement.lineno,end_line=statement.end_lineno,code=segment))
    dump('journal_operations.json',dict(source=journal.relative_to(ROOT).as_posix(),method='ast.parse + ast.literal_eval numeric table only; never exec/replay',operations=operations,job_events=messages,plastic_tables=tables))
    warnings=[]
    context=None
    msg=(selected/'Job-1.msg').read_text(encoding='utf-8',errors='replace').splitlines()
    for i,line in enumerate(msg):
        if re.search(r'INCREMENT\s+\d+\s+STARTS',line): context=dict(line=i+1,text=line.strip())
        if '***WARNING' in line or '***ERROR' in line or 'DISTORTING EXCESSIVELY' in line:
            warnings.append(dict(line=i+1,context=context,text=' '.join(s.strip() for s in msg[i:i+5]) if '***' in line else line.strip()))
    counts=Counter()
    patterns={'negative_eigenvalues':'***WARNING: THE SYSTEM MATRIX', 'large_strain_increment':'***WARNING: THE STRAIN INCREMENT HAS EXCEEDED',
        'plasticity_not_attempted':'***WARNING: THE STRAIN INCREMENT IS SO LARGE', 'excessive_distortion_warning':'***WARNING: EXCESSIVE DISTORTION',
        'zero_moment':'***WARNING: THERE IS ZERO MOMENT', 'element_distortion_lines':'IS DISTORTING EXCESSIVELY',
        'all_warning_headers':'***WARNING:', 'error_headers':'***ERROR'}
    for key,pat in patterns.items(): counts[key]=sum(pat in line for line in msg)
    sta=(selected/'Job-1.sta').read_text().splitlines()
    attempts=[]
    for line in sta:
        p=line.split()
        if len(p)>=9 and p[0].isdigit() and p[1].isdigit():
            attempts.append(dict(step=int(p[0]),increment=int(p[1]),attempt=p[2],severe=int(p[3]),equilibrium=int(p[4]),iterations=int(p[5]),total_time=float(p[6]),step_time=float(p[7]),time_increment=float(p[8])))
    dump('log_analysis.json',dict(warning_counts=counts,warnings=warnings,sta_attempts=attempts,
        successful_increments=sum('U' not in a['attempt'] for a in attempts),unsuccessful_attempts=sum('U' in a['attempt'] for a in attempts),
        log_completed='Abaqus JOB Job-1 COMPLETED' in (selected/'Job-1.log').read_text(),
        sta_completed='THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in '\n'.join(sta)))
    print(json.dumps(dict(inp={k:v for k,v in static.items() if k not in ['surfaces','relevant_blocks']},
        journal_operations=len(operations),job_events=messages,warning_counts=counts,failed_attempts=sum('U' in a['attempt'] for a in attempts)),indent=2))

if __name__=='__main__': main()
