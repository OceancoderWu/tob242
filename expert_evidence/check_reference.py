"""GPU parity against the separately stored upstream implementation."""
import argparse,importlib.util,json,sys
from pathlib import Path
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/harbor_task/tests'))
from train_eval import load_method,seed_all
from data import collate,read_rows,write_json
from torch_geometric.data import HeteroData,Batch
p=argparse.ArgumentParser();p.add_argument('--upstream',required=True);p.add_argument('--data',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,a.upstream)
from src.model_nbf_fb import NBFdistR,get_margin_loss_term
mod=load_method(ROOT/'workspace/reference/method.py')
seed_all(42);original=NBFdistR(hidden_dim=32,num_layers=9,num_relations=8,facets=4,fp_bp=True,aggr_type='min',eval_mode=True).cuda()
seed_all(42);adapted=mod.build_model().cuda()
assert all(torch.equal(v,adapted.state_dict()[k]) for k,v in original.state_dict().items())
records=[]
for k in range(2,10):
 for b in range(1,4):
  rows=read_rows(a.data/f'test_rcc8_k_{k}_b_{b}.csv')[:2]
  graph,labels=collate(rows,'cuda');samples=[]
  for r in rows:
   samples.append(HeteroData(fw={'x':torch.arange(r['n']).unsqueeze(1)},fw__rel__fw=dict(edge_index=torch.tensor(r['edges']).T.contiguous(),edge_type=torch.tensor(r['rels']),target_edge_index=torch.tensor(r['query']).unsqueeze(1),target_edge_type=torch.tensor([r['label']]))))
  batch=Batch.from_data_list(samples).cuda()
  original.zero_grad(set_to_none=True);adapted.zero_grad(set_to_none=True)
  embeddings,relations=original(batch,use_margin_loss=True)
  seed_all(123);loss=get_margin_loss_term(embeddings,relations,labels,num_negative_samples=1,margin=1.,score_fn='xent',outs_as_left_arg=False)
  logits=adapted(graph)
  seed_all(123);loss2=mod.training_loss(logits,labels)
  with torch.no_grad():old_logits,_=original(batch,use_margin_loss=True,infer=True,score_fn='xent',outs_as_left_arg=False)
  assert torch.allclose(old_logits,logits,atol=1e-6,rtol=1e-6)
  assert torch.allclose(loss,loss2,atol=1e-6,rtol=1e-6)
  loss.backward();loss2.backward();max_grad=0.
  for (name,p1),(name2,p2) in zip(original.named_parameters(),adapted.named_parameters()):
   assert name==name2
   assert (p1.grad is None)==(p2.grad is None)
   if p1.grad is not None:
    assert torch.allclose(p1.grad,p2.grad,atol=1e-6,rtol=1e-5),name
    max_grad=max(max_grad,float((p1.grad-p2.grad).abs().max()))
  records.append(dict(k=k,b=b,max_logit_error=float((logits-old_logits).abs().max()),loss_error=float(abs(loss-loss2)),max_gradient_error=max_grad))
write_json(ROOT/'expert_evidence/reference_parity.json',dict(status='passed',samples_per_group=2,groups=records,total_parameters=sum(p.numel() for p in adapted.parameters()),active_parameters=sum(p.numel() for p in adapted.parameters() if p.grad is not None)))
print('Reference prediction, loss, initialization and gradient parity passed across 24 groups')
