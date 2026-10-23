"""Read an existing private OPJU copy with installed OrgLab; never Execute/Save.

CLI: selected-python read_origin.py PRIVATE_COPY NEW_JSON
This is a data/label reader, not a complete Origin processing-history auditor.
"""
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime
import win32com.client.dynamic as dynamic


def read(source):
    app = dynamic.Dispatch('OrgLab1010.Application')
    app._FlagAsMethod('Load', 'GetDataTree')
    if app.Load(str(source.resolve()), True) is not True:
        raise RuntimeError('OrgLab read-only Load failed')
    def props(obj, names):
        return {name: getattr(obj, name) for name in names}
    def call(obj, name, *args):
        obj._FlagAsMethod(name)
        return getattr(obj, name)(*args)
    result = {'observed_at': datetime.now().astimezone().isoformat(),
              'reader': 'OrgLab1010.Application', 'readonly': True,
              'data_tree': app.GetDataTree(0), 'pages': [], 'graphs': [],
              'all_pages': [props(p, ('Name', 'Type', 'Show')) for p in app.Pages],
              'processing_history': 'UNKNOWN: no complete operation/formula lineage API audited'}
    for page in app.WorksheetPages:
        p = props(page, ('Name', 'LongName', 'Comments', 'Show'))
        p['sheets'] = []
        for sheet in page.Layers:
            s = props(sheet, ('Name', 'LongName', 'Rows', 'Cols', 'Show'))
            s['columns'] = []
            for col in sheet.Columns:
                c = props(col, ('Name', 'LongName', 'Units', 'Comments', 'Type', 'Rows', 'DataFormat', 'Show'))
                c['dataset'] = call(col, 'GetDatasetName')
                c['data'] = call(col, 'GetData', 0, 0, -1, 0)
                s['columns'].append(c)
            p['sheets'].append(s)
        result['pages'].append(p)
    for page in app.GraphPages:
        p = props(page, ('Name', 'LongName', 'Comments', 'Show'))
        p['layers'] = []
        for layer in page.Layers:
            s = {'plots': [], 'labels': []}
            for plot in layer.DataPlots:
                s['plots'].append({'name': plot.Name, 'dataset': call(plot, 'GetDatasetName')})
            for obj in layer.GraphObjects:
                s['labels'].append({'name': obj.Name, 'text': obj.Text})
            p['layers'].append(s)
        result['graphs'].append(p)
    return result


if __name__ == '__main__':
    source, target = map(Path, sys.argv[1:])
    if 'private' not in source.parts or 'private' not in target.parts:
        raise ValueError('Only private working copy and private export accepted')
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    result = read(source)
    after = hashlib.sha256(source.read_bytes()).hexdigest()
    result.update(source_sha256=before, source_unchanged=before == after)
    if before != after:
        raise RuntimeError('Read-only copy changed')
    with target.open('x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
