"""Static contract checks only. Isolation must be enforced by the container host."""
import ast
from pathlib import Path
ALLOWED={'torch','torch_geometric','torch_scatter','networkx','typing','math'}
DENIED={'open','exec','eval','compile','__import__','breakpoint','getattr','setattr','delattr','globals','locals','vars'}
DENIED_ATTR={'load','save','load_state_dict','from_file','tofile','numpy','system','popen','subprocess','hub','distributed','multiprocessing','ctypes','socket','environ'}
def check_method(path):
    tree=ast.parse(Path(path).read_text())
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for name in node.names:
                if name.name.split('.')[0] not in ALLOWED:raise ValueError('Disallowed import '+name.name)
        if isinstance(node,ast.ImportFrom):
            if node.level or (node.module or '').split('.')[0] not in ALLOWED:raise ValueError('Disallowed import')
        if isinstance(node,ast.Name) and node.id in DENIED:raise ValueError('Disallowed name '+node.id)
        if isinstance(node,ast.Attribute) and (node.attr in DENIED_ATTR or (node.attr.startswith('__') and node.attr!='__init__')):raise ValueError('Disallowed attribute '+node.attr)
    names={n.name for n in tree.body if isinstance(n,ast.FunctionDef)}
    if not {'build_model','training_loss'}<=names:raise ValueError('Missing API')
