"""Read-only AST provenance check; imports neither torch nor source modules."""
import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parent
UP=ROOT/'upstream/src'
REF=ROOT.parent/'workspace/reference/method.py'

def top(tree,name,kind):
    return next(node for node in tree.body if isinstance(node,kind) and node.name==name)

def same(a,b):
    return ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)

def main():
    ref=ast.parse(REF.read_text())
    general=ast.parse((UP/'model_nbf_general.py').read_text())
    fb=ast.parse((UP/'model_nbf_fb.py').read_text())
    for name in ['NBFCluttr','NBF_base']:
        assert same(top(general,name,ast.ClassDef),top(ref,name,ast.ClassDef)),name
    for name in ['NBFdistRModule']:
        assert same(top(fb,name,ast.ClassDef),top(ref,name,ast.ClassDef)),name
    for name in ['get_negative_relations','kl_div','xent','out_score','margin_loss','get_score','get_margin_loss_term']:
        assert same(top(fb,name,ast.FunctionDef),top(ref,name,ast.FunctionDef)),name
    original=top(fb,'NBFdistR',ast.ClassDef)
    adapted=top(ref,'NBFdistR',ast.ClassDef)
    for member in original.body:
        if not isinstance(member,ast.FunctionDef):continue
        other=top(adapted,member.name,ast.FunctionDef)
        if member.name=='forward':
            assert same(member.args,other.args)
            assert len(member.body)==len(other.body)==20
            assert all(same(a,b) for a,b in zip(member.body[1:],other.body[1:]))
        else:assert same(member,other),member.name
    print('PASS: upstream EpiGNN core and reference AST match; forward differs only in input Batcher construction')
if __name__=='__main__':main()
