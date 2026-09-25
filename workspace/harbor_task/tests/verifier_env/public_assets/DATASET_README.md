---
license: mit
---
# Systematic, Multipath, disjunctive Spatio-Temporal Reasoning (STaR) benchmark

## Main idea
This is part of the [paper](https://huggingface.co/papers/2407.17396) that was published in ICLR 2025 where further details can be found.

The main idea is to expand the concept of binary relational composition to not just be atomic and require that a model reason over multiple 
paths instead of a single one in contrast with previous art.

This can be seen from the example below contrasting a popular previous benchmark.

![image/png](https://cdn-uploads.huggingface.co/production/uploads/65004ca932d2159207eff2a5/6v24oiimQyG6v4qb4jrSk.png)


## Details
The layout is the same for each dataset in the benchmark. There are two axes of complexity 

1. **k**: the path length between the source and target node and
2. **b**: the number of paths between the source and target nodes 

Each dataset has the following rows:

| Edge Index | Edge Labels | Query Edge | Query Label |
|------------|-------------|------------|-------------|
| [(0,1), ...] | EQ         | (0,5)      | TPP   |

- **Edge Index**: `List[Tuple[int, int]]`. A list of edges characterizing the graph.
- **Edge Labels**: `List[str]`. A list of edge labels corresponding to the edge index.
- **Query Edge**: `Tuple[int, int]`. The target edge that a model needs to predict.
- **Query Label**: `str`. The label corresponding to the query edge.

The training sets marked by `train_*.csv` for RCC-8 and Interval algebra (the semigroups that constitute the datasets) contain small graphs of $k=2,3,4$ and $b=1,2,3$. 

The rest of the datasets are for testing systematic generalization. The target classes are balanced.