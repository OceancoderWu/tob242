"""Static contract checks only. Isolation must be enforced by the container host."""
import ast
from pathlib import Path
import stat
ALLOWED={'torch','torch_geometric','torch_scatter','networkx','typing','math'}
DENIED={'open','exec','eval','compile','__import__','breakpoint','getattr','setattr','delattr','globals','locals','vars'}
DENIED_ATTR={'load','save','load_state_dict','from_file','tofile','numpy','system','popen','subprocess','hub','distributed','multiprocessing','ctypes','socket','environ'}
def check_method(path):
    path=Path(path)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('method.py must be a regular file, not a symlink')
    if path.stat().st_size>262144:
        raise ValueError('method.py exceeds 256 KiB')
    tree=ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for name in node.names:
                if name.name.split('.')[0] not in ALLOWED:raise ValueError('Disallowed import '+name.name)
        if isinstance(node,ast.ImportFrom):
            if node.level or (node.module or '').split('.')[0] not in ALLOWED:raise ValueError('Disallowed import')
            if any(alias.name=='*' for alias in node.names):raise ValueError('Wildcard imports are disallowed')
        if isinstance(node,ast.Name) and node.id in DENIED:raise ValueError('Disallowed name '+node.id)
        if isinstance(node,ast.Name) and node.id.startswith('__'):raise ValueError('Disallowed dunder name '+node.id)
        if isinstance(node,ast.Attribute) and (node.attr in DENIED_ATTR or (node.attr.startswith('__') and node.attr!='__init__')):raise ValueError('Disallowed attribute '+node.attr)
    names={n.name for n in tree.body if isinstance(n,ast.FunctionDef)}
    if not {'build_model','training_loss'}<=names:raise ValueError('Missing API')
