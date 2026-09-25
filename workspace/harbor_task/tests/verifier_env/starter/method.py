import torch
from torch import nn
from torch.nn import functional as F
from torch_geometric.nn import FastRGCNConv

class QueryRGCN(nn.Module):
    """Relation-aware GNN with query markers and inverse edges."""
    def __init__(self, hidden_dim=32, num_relations=8, num_steps=9):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_relations = num_relations
        self.num_steps = num_steps
        self.input = nn.Linear(2, hidden_dim)
        self.layers = nn.ModuleList([
            FastRGCNConv(hidden_dim, hidden_dim, num_relations * 2, aggr='mean')
            for _ in range(num_steps)
        ])
        self.norms = nn.ModuleList([nn.LayerNorm(hidden_dim) for _ in range(num_steps)])
        self.readout = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, num_relations)
        )

    def forward(self, batch):
        src, dst = batch['query_index']
        n = batch['num_nodes']
        flags = torch.zeros((n, 2), device=batch['edge_index'].device)
        flags[src, 0] = 1.0
        flags[dst, 1] = 1.0
        x = self.input(flags)
        edges = torch.cat((batch['edge_index'], batch['edge_index'].flip(0)), dim=1)
        rels = torch.cat((batch['edge_type'], batch['edge_type'] + self.num_relations))
        for layer, norm in zip(self.layers, self.norms):
            x = norm(x + F.relu(layer(x, edges, rels)))
        a, b = x[src], x[dst]
        return self.readout(torch.cat((a, b, a * b, torch.abs(a - b)), dim=-1))


def build_model(num_relations=8, num_steps=9):
    return QueryRGCN(32, num_relations, num_steps)

def training_loss(logits, targets):
    return F.cross_entropy(logits, targets)
