"""Static source lineage check for the previously trained GPU R-GCN."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
old=(ROOT/'results/rgcn_pair_v1/model.py').read_text()
new=(ROOT/'tob242/workspace/harbor_task/solution/method.py').read_text()
expected=old.replace("        data = batch['fw', 'rel', 'fw']\n        src, dst = data.target_edge_index\n        n = batch['fw'].num_nodes", "        src, dst = batch['query_index']\n        n = batch['num_nodes']").replace('data.edge_index',"batch['edge_index']").replace('data.edge_type',"batch['edge_type']")
assert new.startswith(expected)
remainder=new[len(expected):]
assert 'def build_model(' in remainder and 'def training_loss(' in remainder
print('PASS: R-GCN architecture matches prior trained model; graph container and API wrapper changed')
