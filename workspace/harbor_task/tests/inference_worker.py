"""Low-privilege model process. Requests contain graph inputs and no labels."""
import argparse
import contextlib
import importlib.util
import json
import sys
from pathlib import Path

import torch
from data import collate
from security import check_method


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--method', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--num-steps', type=int, required=True)
    args = parser.parse_args()
    check_method(args.method)
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required')
    protocol_out = sys.stdout
    with contextlib.redirect_stdout(sys.stderr):
        spec = importlib.util.spec_from_file_location('candidate_inference', args.method)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        model = module.build_model(num_relations=8, num_steps=args.num_steps).to('cuda')
        checkpoint = torch.load(args.checkpoint, map_location='cuda')
        model.load_state_dict(checkpoint['model'])
        model.eval()
    for line in sys.stdin:
        inputs = json.loads(line)
        if not isinstance(inputs, list) or not inputs or len(inputs) > 128:
            raise ValueError('Invalid input batch')
        with contextlib.redirect_stdout(sys.stderr), torch.no_grad():
            graph, _ = collate(inputs, 'cuda', include_labels=False)
            logits = model(graph)
            if logits.shape != (len(inputs), 8) or not torch.isfinite(logits).all():
                raise ValueError('Expected finite [batch,8] logits')
            predictions = logits.argmax(-1).cpu().tolist()
        protocol_out.write(json.dumps(predictions) + '\n')
        protocol_out.flush()


if __name__ == '__main__':
    main()
