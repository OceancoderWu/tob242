# Adapted from erg0dic/gnn-sg; MIT license in LICENSE.upstream.
from torch_scatter.composite import scatter_softmax
from torch_scatter import scatter_add, scatter
from torch_geometric.nn import MessagePassing
import torch
import torch.nn as nn
from torch.nn.functional import normalize
from typing import Union

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

class Logits:
    pass
class Probas:
    pass

def entropy(probas, axis=0, eps=1e-8):
    "add a small eps as I want to avoid the log(0)=-inf val"
    out =  -1*(probas*torch.log(probas+eps)).sum(axis=axis)
    return out

def stable_norm_denominator(vector_batch, vec_dim=-1):
    # unused so far... but smart money bets it will be useful later
    norms = torch.norm(vector_batch, dim=vec_dim)
    norms[norms==0] = 1
    return norms.unsqueeze(-1)

def compute_sim(input, relation_in_proto_basis, type='cosine', einsum_str: str = None):
    if einsum_str is None:
        einsum_str = "nh, ph -> np"
    if type == 'cosine':
        # normalize vectors without hitting the zeros
        input = normalize(input)
        relation_in_proto_basis = normalize(relation_in_proto_basis)
        sims = torch.einsum(einsum_str, input, relation_in_proto_basis)
        return sims
    elif type=='euclidean':
        EPS=1e-8
        x = relation_in_proto_basis-input.unsqueeze(1)
        dist = torch.pow((x*x).sum(axis=-1), 0.5)
        return torch.log((dist+1)/(dist+EPS))
    else:
        raise NotImplementedError(f"Distance type {type} has not been implemented.")
    
def make_probas(x: torch.Tensor):
    # hacky? is it even worth testing or should I just use softmax on logprobs?
    return torch.abs(x) / x.sum(dim=-1).unsqueeze(-1)

def sample_gumbel(shape, eps=1e-10):
    # from G(0,1)
    # stablize cf. https://gist.github.com/GongXinyuu/3536da55639bd9bfdd5a905ebf3ab88e
    U = torch.rand(shape, device=device)
    gumbles = -torch.log(-torch.log(U + eps) + eps)
    if torch.isnan(gumbles).any() or torch.isinf(gumbles).any():
        gumbles = sample_gumbel(shape, eps=eps)
    return gumbles

def gumbel_softmax_sample(logits: Logits, 
                          temperature=.7, 
                          dim=-1, 
                          eval_mode=False, 
                          just_discretize=False, 
                          ys_are_probas=False) -> Union[Logits, Probas]:
    if eval_mode:
        if ys_are_probas:
            return torch.softmax(logits, dim=-1)
        else:
            return logits
    # from Gumbel Softmax
    y = logits if just_discretize else logits + sample_gumbel(logits.shape)
    SO = torch.softmax if ys_are_probas else torch.log_softmax
    out =  SO(y / temperature, dim=dim)

    return out

class NBFCluttr(MessagePassing):
    def __init__(self, num_relations, hidden_dim, num_prototypes, 
                 dist='cosine', fix_ys=False):
        super().__init__()
        # mapping to multiple prototypes basis from 1 relation
        # Note the num_protos p can in fact be > num_relations r 
        # for the y(i,r) basis vectors of the message passing function
        if fix_ys:
            self.multi_embedding = (torch.rand(size=(num_relations, num_prototypes, hidden_dim), device=device))
        else:
            self.multi_embedding = nn.Parameter(torch.rand(size=(num_relations, num_prototypes, hidden_dim), device=device))
        # for the probas
        self.proto_embedding = nn.Parameter(torch.rand(size=(num_prototypes, hidden_dim)))
        self.dist = dist
        self.layer_norm = nn.LayerNorm(hidden_dim)
        self.activation = nn.ReLU() 
        self.linear = nn.Linear(hidden_dim * 2, hidden_dim)


    def forward(self, input, edge_index, edge_type, return_probas=False):
        return self.propagate(edge_index=edge_index, input=input, edge_type=edge_type,
                              return_probas=return_probas, num_nodes=input.shape[0])
    
    def look_up_rel_proto_vectors(self, batch_edge_indices):
        rel_basis = self.multi_embedding.index_select(0, batch_edge_indices)
        return rel_basis
    
    def message(self, input_j, edge_type):
        'the direction of propagation by default is o --> o i.e. left to right source-to-target.'
        # `input_j` just copies over the node vectors for each head in `edge_index`
        # so thinking we have a 2-D tensor (num_nodes, hidden_dim)
        # this will need to be the output shape too!
        rel_proto_basis = self.look_up_rel_proto_vectors(edge_type)
        proto_probas = self.project_nodes_onto_proto_simplex(input_j, self.proto_embedding, 
                                                             dist_type=self.dist)
        # compute entropy of each prototype vector in the proto basis
        out = torch.einsum("np, nph -> nh", proto_probas, rel_proto_basis)
        return out, proto_probas
        
    def aggregate(self, input, index, num_nodes):
        input_j, proto_proba = input # proto_proba is (protos, num_nodes)
        # add self loops to index
        proto_entropy = entropy(proto_proba, axis=1) 
        # the rest need to be scatter operations since they are over the node dimension
        entropic_attention_coeffs = scatter_softmax(-proto_entropy, index)
        out = torch.einsum('n, nh-> nh', entropic_attention_coeffs, input_j)
        out = scatter_add(out, index, dim=0, dim_size=num_nodes) # in the node dimension
        
        return out, proto_proba
    
    def project_nodes_onto_proto_simplex(self, inp, proto_basis, 
                                        dist_type='cosine'):
        # take a dot product between an `inp` node embedding vector 
        # and each prototypical relation vector and then softmax over the proto dim
        # if len(proto_basis.shape) == 2:
        #     proto_basis = proto_basis.expand(inp.shape[0], *proto_basis.shape)
        proto_input_overlap = compute_sim(inp, proto_basis, 
                                          type=dist_type)
        # This is scatter-invariant Because we have essentially copied 
        # over all prototypes for each edge input and taken a softmax 
        # over the prototypical basis.
        proto_proba = torch.softmax(proto_input_overlap, dim=1)
        return proto_proba

    def update(self, update, input, return_probas=False, mix_inp_out=False):
        # node update as a function of old states (input) [THIS IS THE INPUT TO `forward`] and this layer output (update)
        # print(update.shape, input.shape)
        new_out, proto_proba = update
        if mix_inp_out:
            output = self.linear(torch.cat([input, new_out], dim=-1))
            if self.layer_norm:
                output = self.layer_norm(output)
            if self.activation:
                output = self.activation(output)
        
        if return_probas:
            return new_out, proto_proba
        else:
            return new_out
        

class NBF_base(nn.Module):
    def __init__(self):
        super().__init__()

    def post_init(self):
        raise NotImplementedError
    
    @staticmethod
    def get_mlp_classifier(num_mlp_layer, hidden_dim, out_dim, middle_dim=None):
        nn.Sequential()
        mlp = []
        for i in range(num_mlp_layer - 1):
            if middle_dim:
                if i==0:
                    mlp.append(nn.Linear(hidden_dim, middle_dim))
                else:
                    mlp.append(nn.Linear(middle_dim, middle_dim))
            else:
                mlp.append(nn.Linear(hidden_dim, hidden_dim))
            mlp.append(nn.Tanh())
        mlp.append(nn.Linear(middle_dim if middle_dim else hidden_dim, out_dim))
        return nn.Sequential(*mlp)

    def make_boundary(self, batch, source_embedding):
        raise NotImplementedError

    def forward(self, batch):
        raise NotImplementedError
    
    def apply_classifier(self, hidden, tail_indices):
        raise NotImplementedError

        

import networkx as nx
class Batcher:
    def __init__(self, num_nodes, edge_index, edge_type, target_edge_index):
        self.num_nodes=num_nodes
        self.edge_index=edge_index
        self.edge_type=edge_type
        self.target_edge_index=target_edge_index

def get_shortest_path_indices_from_edge_index(edge_index, target_edge_index):
    graph=nx.Graph()
    graph.add_edges_from(edge_index.detach().cpu().T.tolist())
    indices, groups=[], []
    for i,(source,target) in enumerate(target_edge_index.detach().cpu().T.tolist()):
        path=nx.single_source_bellman_ford_path(graph,source)[target]
        indices.extend(path)
        groups.extend([i]*len(path))
    return indices,groups
"""
The main idea for the forward/backward model is to propagate information from the source 
and the tail of the data graph and try to generate inferences by concatenating intermediate 
representations of the forward and backward models. 

This is motivated by the idea that the relational composition complexity (loosely inferrable 
from the probability of a composition landing outside the set of prototypical or known relations)
is smaller for some non-contiguous subgraph composition than starting the composition 
from privileged positions (source/sink).

The recipe from an implementation POV is:
    1. **We use the same model for forward and backward propagation.**
    2. There will be two sets of identical but reversed data batches per propagation pass.
    3. Two *different* source/sink embeddings will be initialized for forward and backward propagation.
"""
import torch
import torch.nn as nn
from torch_scatter import scatter_min, scatter_softmax, scatter_add, scatter_mul, scatter_logsumexp

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

def get_negative_relations(relations, target_inds, num_negative_samples=10):
    batch_size = target_inds.shape[0]
    num_relations = relations.shape[0]
    repeated_relations_inds = torch.arange(num_relations, device=device).repeat(batch_size, 1)
    mask = repeated_relations_inds == target_inds.unsqueeze(-1)
    sampling_matrix = repeated_relations_inds[~mask].reshape(-1, num_relations-1)
    inds_to_pick = torch.randint(0, num_relations-1, (batch_size, num_negative_samples), device=device)
    negative_relations_inds = sampling_matrix[torch.arange(batch_size).unsqueeze(-1), inds_to_pick]
    assert not (negative_relations_inds == target_inds.unsqueeze(-1)).any(), 'target relation in negative samples!'
    negative_relations = relations[negative_relations_inds]
    return negative_relations

def kl_div(p, q, eps=1e-12):
    P = p+eps
    Q = q+eps
    kl_bnf = (P*torch.log(P/Q)).sum(axis=-1)
    return kl_bnf

def xent(p, q, eps=1e-12):
    """
    NOTE: q is logged
    -----
    """
    P = p
    Q = q+eps
    xent_bnf = -1*(P*torch.log(Q)).sum(axis=-1)
    return xent_bnf

def out_score(outs_bfh, rs_rfh, score_fn='kl', outs_as_left_arg=True):
    num_relations = rs_rfh.shape[0]
    batch_size = outs_bfh.shape[0]
    rs_brfh = rs_rfh.unsqueeze(0).repeat(batch_size, 1, 1, 1)
    outs_brfh = outs_bfh.unsqueeze(1).repeat(1, num_relations, 1, 1)
    if outs_as_left_arg:
        score_br = get_score(outs_brfh, rs_brfh, score_fn=score_fn).sum(axis=-1)
    else:
        score_br = get_score(rs_brfh, outs_brfh, score_fn=score_fn).sum(axis=-1)
    return score_br

def margin_loss(score_negative_b, score_positive_b, margin=0.1):
    # sum over the facet dim and the batch dim
    margin_1 = torch.clamp_min(score_positive_b - score_negative_b + margin, 0)
    return margin_1.mean()

def get_score(left_arg, right_arg, score_fn='kl'):
    if score_fn == 'kl':
        score_bnf = kl_div(left_arg, right_arg)
    elif score_fn == 'xent':
        score_bnf = xent(left_arg, right_arg)
    else:
        raise ValueError(f"score_fn must be one of ['kl', 'xent'] but got {score_fn}")
    return score_bnf

def get_margin_loss_term(outs_bfh, rs_rfh, targets, num_negative_samples=10, margin=0.1, score_fn='kl', 
                         outs_as_left_arg=True):
    neg_samples_bnfh = get_negative_relations(rs_rfh, targets, num_negative_samples=num_negative_samples)
    if outs_as_left_arg:
        left_neg, right_neg = outs_bfh.unsqueeze(1), neg_samples_bnfh
        left_pos, right_pos = outs_bfh, rs_rfh[targets]
    else:
        right_neg, left_neg = outs_bfh.unsqueeze(1), neg_samples_bnfh
        right_pos, left_pos = outs_bfh, rs_rfh[targets]

    neg_score_bnf = get_score(left_neg, right_neg, score_fn=score_fn)
    neg_score_b = neg_score_bnf.mean(axis=-1).mean(axis=-1)

    pos_score_bf = get_score(left_pos, right_pos, score_fn=score_fn)
    pos_score_b = pos_score_bf.mean(axis=-1)

    margin_1 = margin_loss(neg_score_b, pos_score_b, margin=margin)

    return margin_1

def softmax_with_max_norm(x):
    exp_x = torch.exp(x)
    return exp_x/exp_x.max(axis=-1)[0].unsqueeze(-1)

class NBFdistRModule(NBFCluttr):
    def __init__(self, num_relations, hidden_dim, 
                 eval_mode=False, temperature=0.7, 
                 just_discretize=False, 
                 facets=1,
                 aggr_type:str=None, 
                 ablate_compose:bool=False,
                 ablate_probas:bool=False,
                 ):
        # parallelized over facets aka. distributed representations
        super().__init__(num_relations, hidden_dim, num_relations)
        self.facets=facets
        self.new_hidden_dim = hidden_dim//self.facets
        # relation independent bilinear composition map: A: r1 ∘ r2 ⤇ r3
        self.learn_A = torch.rand(self.facets, 
                                  self.new_hidden_dim, 
                                  self.new_hidden_dim-1, 
                                  self.new_hidden_dim-1, device=device)*2 - 1
        
        self.learn_A_subspace = nn.Parameter(self.learn_A)


        self.r_embedding = nn.Parameter(torch.rand(size=(num_relations, self.facets, 
                                                         self.new_hidden_dim), device=device)*2-1)
        #  try another init method to see if results improve? based on my dirty analysis, uniform random was beneficial 
        #  for avoiding early one hot saturation
        torch.nn.init.xavier_uniform_(self.r_embedding)
        torch.nn.init.xavier_uniform_(self.learn_A)

        self.multi_embedding = self.r_embedding
        self.eval_mode = eval_mode
        self.just_discretize = just_discretize
        self.temperature = temperature
        self.aggr_type = aggr_type

        self.relu = nn.ReLU()
        self.identity = nn.Identity()

        self.drop1 = nn.Dropout(0.3)
        self.drop2 = nn.Dropout(0.4)

        self.mlp_composer = NBF_base.get_mlp_classifier(4, self.new_hidden_dim, self.new_hidden_dim, 300)
        self.ablate_compose = ablate_compose
        self.ablate_probas = ablate_probas

    def forward(self, input, edge_index, edge_type, return_probas=False, forward=True):
        return self.propagate(edge_index=edge_index, input=input, edge_type=edge_type,
                              return_probas=return_probas,
                              forward=forward, num_nodes=input.shape[0],
                              )
    
    def look_up_rel_proto_vectors(self, batch_edge_indices):
        rel_basis = self.r_embedding.index_select(0, batch_edge_indices)
        return rel_basis

    def message(self, input_j, edge_type, forward=False):
        # N.B.: we do not softmax the node embeddings since they are expected to 
        # already be probas of the form
        #               sources: [[1, ..., 0], [1, ..., 0], [1, ..., 0]]
        #               others:  [[1/n, ..., 1/n], [1/n, ..., 1/n], [1/n, ..., 1/n]]
        input_j = input_j.reshape(*input_j.shape[:-1], self.facets, self.new_hidden_dim)
        assert input_j.shape[-1] == self.new_hidden_dim, "dim rounding error in facet reshaping of source/input embeddings."
        # these are the logprob relation vectors: basically each edge type is mapped to a vector
        rel_proto_basis = self.look_up_rel_proto_vectors(edge_type) 
        rel_proto_basis = torch.softmax(rel_proto_basis, axis=-1)

        if forward:
            arg_l, arg_r = input_j, rel_proto_basis
        else:
            arg_r, arg_l = input_j, rel_proto_basis
        if  self.ablate_compose:
            composition = self.ablation_compose(arg_l, arg_r)
        else:
            # bilinear message function where crucially r ∘ h ↔ ϕ(r, h) ≠ ϕ(h, r) ↔ h ∘ r
            composition = self.compose(arg_l, arg_r)
        return composition
    
    def compose(self, r1, r2):
        """
        prob mods: know that we can't do a softmax over As without ruining the one-hot components. So instead:
            1. make sure all A entries are positive 
            2. make sure the result of the composition satisfies the prob sun axiom in the final dim. 
        """
        assert r1.shape == r2.shape, f"r1 and r2 must have the same shape but got {r1.shape} and {r2.shape}"
        A = self.get_A()
        composition = lambda a: torch.einsum("nfi, fpij, nfj -> nfp", r1, a, r2)
        out = composition(A)
        if not self.ablate_probas:
            assert torch.allclose(out.sum(axis=-1), torch.tensor(1.)), "composed prob vecs not normalized"
        return out

    def ablation_compose(self, r1, r2):
        assert r1.shape == r2.shape, f"r1 and r2 must have the same shape but got {r1.shape} and {r2.shape}"
        out = (torch.abs(self.mlp_composer(r1)) + 1e-18)*(torch.abs(self.mlp_composer(r2)) + 1e-18)
        if not self.ablate_probas:
            out /= out.sum(axis=-1).unsqueeze(-1)
            assert torch.allclose(out.sum(axis=-1), torch.tensor(1.)), "composed prob vecs not normalized"
        return out

    def get_A(self):
        # https://discuss.pytorch.org/t/require-gradient-only-for-some-tensor-elements-others-should-be-held-constant/24429/3
        # make the As so that the grads are selectively backpropped
        # TODO: can this be optimized?
        A = torch.zeros((self.facets, self.new_hidden_dim,  self.new_hidden_dim, self.new_hidden_dim), device=device)
        # add left arg constraint in Φ((1,0, ..., 0), h) = (1,0, ..., 0)^TAh = Σ_j δ_{1j} * h_j = h 
        A[..., 0, :]  = torch.eye(self.new_hidden_dim)
        # repeat for right arg
        A[..., 0,]  = torch.eye(self.new_hidden_dim)
        if self.ablate_probas:
            A[..., 1:, 1:] += self.learn_A_subspace
            X=A
        else:
            A[..., 1:, 1:] += torch.softmax(self.learn_A_subspace, axis=-1)
            X = self.normalise_A(A)
        return X
    
    def normalise_A(self, A):
        # this applies the vector normalisation on A without hitting the one-hots
        perm_A = A.permute(0, 3, 2, 1)
        perm_A /= perm_A.sum(dim=-1).unsqueeze(-1)
        out = perm_A.permute(0, 3, 2, 1)
        return out
    
    def aggregate(self, input, index, num_nodes, smax_free_attention=False):
        # inputs are (num_nodes_per_batch, facets, hidden_dim)
        # do parallel node aggregation over the facets

        if self.aggr_type == 'mul':
            out = scatter_mul(input, index, dim=0, dim_size=num_nodes) + 1e-18
        elif self.aggr_type == 'min':
            out = scatter_min(input, index, dim=0, dim_size=num_nodes)[0] + 1e-18
        else:
            raise NotImplementedError(f'{self.aggr_type} aggregation operation is not supported')

        if not self.ablate_probas:
            out /= out.sum(axis=-1).unsqueeze(-1)
            assert torch.allclose(out.sum(axis=-1), torch.tensor(1.)), 'aggr prob vecs not normalized'

        return out, out

class NBFdistR(NBF_base):
    def __init__(self, hidden_dim, residual=False,
                 num_layers=9, num_relations=18, 
                 shared=True, dist='cosine', 
                 facets=2,
                 use_mlp_classifier=False, fix_ys=False, 
                 eval_mode=False, temperature=0.7, 
                 fp_bp=False, just_discretize=False,
                 ys_are_probas=False,
                 aggr_type:str='mul',
                 ablate_compose:bool=False,
                 ablate_probas:bool=False):

        super().__init__()
        # prop through only the first layer at each message-passing round 
        assert shared == True, 'this model is designed for a single message passing layer'
        self.shared = shared
        self.hidden_dim = hidden_dim
        self.num_relations = num_relations
        self.facets = facets
        self.residual = residual
        self.eval_mode = eval_mode
        self.just_discretize = just_discretize
        # self.eval_mode = True
        self.temperature = temperature

        self.source_embedding = self.make_init_fixed_embeddings()
        self.BF_layers = nn.ModuleList()
        self.mlp = self.get_mlp_classifier(3, hidden_dim, hidden_dim)
        self.linear = nn.Linear(num_relations, num_relations)
        self.linear_margin = nn.Linear(hidden_dim//facets, hidden_dim//facets)
        self.relu = nn.ReLU()
        self.ablate_probas = ablate_probas

        for i in range(num_layers):
            self.BF_layers.append(NBFdistRModule(num_relations, hidden_dim,
                                                facets=self.facets,
                                                eval_mode=self.eval_mode, 
                                                temperature=temperature, 
                                                just_discretize=self.just_discretize,
                                                aggr_type=aggr_type,
                                                ablate_compose=ablate_compose,
                                                ablate_probas=ablate_probas))
            
    def make_init_fixed_embeddings(self) -> torch.Tensor:
        assert self.hidden_dim % self.facets == 0, "Hidden dim must be divisible by the number of facets."
        source = torch.zeros((self.facets, self.hidden_dim//self.facets), device=device)
        source[:,0] = 1
        return source.reshape(-1)
    
    def one_it_source_embeddings(self, batch, source_embeddings, forward=True):
        shape = source_embeddings.shape
        if len(shape) > 2:
            source_embeddings = source_embeddings.reshape(*shape[:-2], -1)
        # location of the source nodes
        index = batch.target_edge_index[0] if forward else batch.target_edge_index[1]
        source_embeddings[index] =  self.source_embedding # a bunch of indicators
        return source_embeddings.reshape(shape)
        
    def make_boundary(self, batch, forward=True):
        num_nodes = batch.num_nodes
        se_dim_size = self.source_embedding.shape[-1]

        source_embeddings = torch.zeros(size=(num_nodes, se_dim_size), device=device)
        source_embeddings = self.one_it_source_embeddings(batch, source_embeddings, forward=forward)
        # now add the filling for every other node
        # uniform (max entropy filling)
        not_sources_ind = torch.arange(num_nodes, device=device)
        if forward:
            not_sources_ind = not_sources_ind[~torch.isin(not_sources_ind, batch.target_edge_index[0])]
        else:
            not_sources_ind = not_sources_ind[~torch.isin(not_sources_ind, batch.target_edge_index[1])]
        repeated_filling = torch.ones((not_sources_ind.shape[0], se_dim_size), device=device) / (self.hidden_dim//self.facets)
        source_embeddings[not_sources_ind] =  repeated_filling
        return source_embeddings
    
    def do_a_graph_prop(self, batch, forward=True):
        boundary = self.make_boundary(batch, forward=forward)
            
        inp = boundary
        for i in range(len(self.BF_layers)):
            return_probas = True if i == len(self.BF_layers) - 1 else False
            if self.shared:
                if forward:
                    self.BF_layers[0].flow = 'source_to_target'
                else:
                    self.BF_layers[0].flow = 'target_to_source'
                hidden = self.BF_layers[0](inp, batch.edge_index, batch.edge_type,
                                           return_probas=return_probas,
                                           forward=forward, 
                                        )
            else:
                if forward:
                    self.BF_layers[0].flow = 'source_to_target'
                else:
                    self.BF_layers[0].flow = 'target_to_source'
                hidden = self.BF_layers[i](inp, batch.edge_index, batch.edge_type, 
                                           return_probas=return_probas,
                                           forward=forward,
                                        )
            if return_probas:
                hidden, probas = hidden
            if self.residual:
                hidden = hidden + inp
            # The boundary is initialized as a fixed embedding that already satisfies the prob axioms
            # N.B.: cannot add unconditional self loops to fix the message disappearance problem after aggregation.
            inp = self.one_it_source_embeddings(batch, hidden, forward=forward).reshape(*inp.shape)
    
        return hidden, probas

    def forward(self, batch_fb, fw_only=False, bw_only=False, 
                use_margin_loss=False, 
                final_linear=False, outs_as_left_arg=True, 
                score_fn='kl', infer=False, activate_infer_lens=False):
        # TODO(redundant): replace
        # preprocess batch to make batch (forward) and batch_rev compatible with rest of the code
        batch = Batcher(num_nodes=batch_fb['num_nodes'],
                        edge_index=batch_fb['edge_index'],
                        edge_type=batch_fb['edge_type'],
                        target_edge_index=batch_fb['query_index'])
        # h→
        hidden, probas = self.do_a_graph_prop(batch, forward=True)
        # h←
        hidden_r, probas_r = self.do_a_graph_prop(batch, forward=False)
        #       currently just whittling down the hidden indices for single shortest paths 
        #       between source and sink before applying the aggregation
        filtered_inds, agg_index = get_shortest_path_indices_from_edge_index(batch.edge_index, batch.target_edge_index) 
        filtered_hidden = hidden[filtered_inds] 
        filtered_hidden_r = hidden_r[filtered_inds]

        # time for inference: first compose h→ and h←
        final_h = self.BF_layers[0].compose(filtered_hidden, filtered_hidden_r)
        
        # these tests fail due to cycles in the graphs
        # assert torch.allclose(final_h[0], filtered_hidden_r[0]), f"final h← (since flipped) needs to be invariant to composition with one-hot source {breakpoint()}"
        # assert torch.allclose(final_h[-1], filtered_hidden[-1]), f"final h→ needs to be invariant to composition with one-hot source {breakpoint()}"
        
        # `num_nodes` is none to just get ordered final prediction embeddings
        out_embeddings_bfh, out_probas = self.BF_layers[0].aggregate(final_h, torch.tensor(agg_index, device=device), num_nodes=None)

        if fw_only:
            out_embeddings_bfh = hidden[batch.target_edge_index[1]]
        elif bw_only:
            out_embeddings_bfh = hidden_r[batch.target_edge_index[0]]
        assert out_embeddings_bfh.shape[0] == batch.target_edge_index.shape[-1], "Output embeddings should be of the same length as the number of target nodes."
        # now find overlap with relation vectors
        
        rs_rfh = torch.softmax(self.BF_layers[0].r_embedding, axis=-1)
        if self.ablate_probas:
            out_embeddings_bfh = torch.abs(out_embeddings_bfh)
            out_embeddings_bfh /= out_embeddings_bfh.sum(axis=-1).unsqueeze(-1)
        
        if use_margin_loss:
            if final_linear:
                out_embeddings_bfh = self.relu(self.linear_margin(out_embeddings_bfh))
            if infer:
                outs_br = -1*out_score(out_embeddings_bfh, rs_rfh, score_fn=score_fn, outs_as_left_arg=outs_as_left_arg)
                return outs_br, probas
            elif not activate_infer_lens:
                return out_embeddings_bfh, rs_rfh
        if activate_infer_lens:
            return hidden, hidden_r, filtered_hidden, filtered_hidden_r, out_embeddings_bfh
        
        out_embeddings_bh = out_embeddings_bfh.reshape(*out_embeddings_bfh.shape[:-2], -1)
        rs_rh = rs_rfh.reshape(*rs_rfh.shape[:-2], -1)
        
        
        outs = compute_sim(out_embeddings_bh, rs_rh, type='cosine', einsum_str='nh, rh -> nr')
        # note that outs is never going to be negative since it is the result of a dot product over prob vectors. so taking the log is NECESSARY.
        logits = torch.log(outs+1e-16)
        if final_linear:
            logits = self.linear(outs)
        # logits = outs
        # truncate the logits to the top num_relations to impose a perf improving (inductive) bias [Exp. suggests: yes.]
        if self.hidden_dim == self.num_relations:
            return logits, probas
        else:
            # note that the base case is when logit[dim -1] equals number of relations 
            return logits[:,:self.num_relations], probas[:,:self.num_relations]
        
    
class Reference(NBFdistR):
    def forward(self, graph):
        logits,_=super().forward(graph,use_margin_loss=True,infer=True,
                               score_fn='xent',outs_as_left_arg=False)
        return logits

def build_model(num_relations=8,num_steps=9):
    return Reference(hidden_dim=32,num_layers=num_steps,num_relations=num_relations,
                     facets=4,fp_bp=True,aggr_type='min',eval_mode=True)

def training_loss(logits,targets):
    # Upstream inference sums facets; its margin loss averages them.
    scores=logits/4
    choices=torch.arange(scores.shape[1],device=scores.device).repeat(len(targets),1)
    choices=choices[choices != targets[:,None]].reshape(len(targets),-1)
    pick=torch.randint(0,scores.shape[1]-1,(len(targets),1),device=scores.device)
    negative=choices.gather(1,pick).squeeze(1)
    rows=torch.arange(len(targets),device=scores.device)
    return torch.clamp_min(1-scores[rows,targets]+scores[rows,negative],0).mean()
