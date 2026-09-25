import ast
import csv
import hashlib
import json
from pathlib import Path
import torch

LABELS=['DC','EC','EQ','NTPP','NTPPI','PO','TPP','TPPI']
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()

def verify(train_data_dir,test_data_dir,manifest):
    entries=[(train_data_dir,manifest['train_file'])]
    entries.extend((test_data_dir,item) for item in manifest['test_files'])
    for data_dir,item in entries:
        if sha(Path(data_dir)/item['file']) != item['sha256']:
            raise ValueError('Dataset hash mismatch: '+item['file'])

def read_rows(path):
    rows=[]
    with Path(path).open(newline='') as f:
        for r in csv.DictReader(f):
            edges=ast.literal_eval(r['edges']);query=ast.literal_eval(r['query_edge'])
            names=ast.literal_eval(r['edge_labels'])
            assert len(edges)==len(names)
            rows.append(dict(edges=edges,rels=[LABELS.index(x) for x in names],query=query,
                             label=LABELS.index(r['query_label']),n=max(max(e) for e in edges)+1))
    return rows

def collate(rows,device):
    edges=[];rels=[];queries=[];groups=[];offset=0
    for i,r in enumerate(rows):
        edges.extend((a+offset,b+offset) for a,b in r['edges'])
        rels.extend(r['rels']);queries.append([x+offset for x in r['query']])
        groups.extend([i]*r['n']);offset+=r['n']
    graph=dict(edge_index=torch.tensor(edges,dtype=torch.long,device=device).T.contiguous(),
               edge_type=torch.tensor(rels,dtype=torch.long,device=device),
               query_index=torch.tensor(queries,dtype=torch.long,device=device).T.contiguous(),
               batch=torch.tensor(groups,dtype=torch.long,device=device),num_nodes=offset)
    labels=torch.tensor([r['label'] for r in rows],dtype=torch.long,device=device)
    return graph,labels

def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(path)
