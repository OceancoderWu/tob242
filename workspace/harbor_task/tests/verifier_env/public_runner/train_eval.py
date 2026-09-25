"""Trusted common trainer. Models receive graph inputs only, never target labels."""
import argparse
import importlib.util
import json
import random
import sys
import time
from pathlib import Path
import numpy as np
import torch
from data import collate,read_rows,sha,verify,write_json,LABELS
from security import check_method

TASK=Path('/workspace') if Path('/workspace/environment/public_assets').is_dir() else Path(__file__).resolve().parents[1]
ASSETS=TASK/'environment/public_assets'

def load_method(path):
    spec=importlib.util.spec_from_file_location('candidate_method',path)
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    return mod

def seed_all(seed):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False

def evaluate(model,rows,bs,device):
    model.eval();correct=0;predictions=[]
    with torch.no_grad():
        for i in range(0,len(rows),bs):
            graph,labels=collate(rows[i:i+bs],device);logits=model(graph)
            if logits.shape!=(len(labels),8) or not torch.isfinite(logits).all():
                raise ValueError('Expected finite [batch,8] logits')
            pred=logits.argmax(-1);correct+=int((pred==labels).sum());predictions.extend(pred.cpu().tolist())
    import hashlib
    return dict(correct=correct,total=len(rows),accuracy=correct/len(rows),
                predictions_sha256=hashlib.sha256(bytes(predictions)).hexdigest())

def main():
    p=argparse.ArgumentParser();p.add_argument('--method',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--data',type=Path,default=ASSETS/'data');p.add_argument('--test-data',type=Path,default=Path('/tests/benchmark_data'));p.add_argument('--smoke',action='store_true')
    p.add_argument('--public-dev',action='store_true',help='Train and score only the public validation split; never read benchmark tests')
    p.add_argument('--reload',type=Path);args=p.parse_args()
    cfg=json.loads((ASSETS/'protocol.json').read_text());manifest=json.loads((ASSETS/'manifest.json').read_text())
    public_dev=args.public_dev or args.smoke
    verify(args.data,args.test_data,manifest,include_tests=not public_dev)
    check_method(args.method)
    if not torch.cuda.is_available():raise RuntimeError('CUDA GPU required')
    torch.set_num_threads(4);seed_all(args.seed);device=torch.device('cuda')
    args.output.mkdir(parents=True,exist_ok=False)
    rows=read_rows(args.data/manifest['train_file']['file'])
    train_set,val_set=torch.utils.data.random_split(rows,[.8,.2])
    split=dict(train_indices=train_set.indices,val_indices=val_set.indices,seed=args.seed)
    write_json(args.output/'split.json',split)
    train=list(train_set);val=list(val_set)
    if args.smoke:train=train[:256];val=val[:128]
    module=load_method(args.method);model=module.build_model(num_relations=8,num_steps=cfg['num_steps']).to(device)
    params=sum(p.numel() for p in model.parameters())
    if params>cfg['max_parameters']:raise ValueError('Parameter cap exceeded')
    write_json(args.output/'config.json',{**cfg,'seed':args.seed,'smoke':args.smoke,'labels':LABELS})
    provenance=dict(method_sha256=sha(args.method),trainer_sha256=sha(__file__),data_loader_sha256=sha(Path(__file__).with_name('data.py')),
                    protocol_sha256=sha(ASSETS/'protocol.json'),manifest_sha256=sha(ASSETS/'manifest.json'),
                    split_sha256=sha(args.output/'split.json'),torch=torch.__version__,cuda=torch.version.cuda,
                    gpu=torch.cuda.get_device_name(),parameters=params,train_rows=len(train),val_rows=len(val))
    write_json(args.output/'provenance.json',provenance)
    start=time.time();torch.cuda.reset_peak_memory_stats();best=-1.;epoch_best=None
    if args.reload:
        checkpoint=torch.load(args.reload,map_location=device)
        if checkpoint['method_sha256']!=sha(args.method):raise ValueError('Checkpoint method mismatch')
        if checkpoint['seed']!=args.seed or checkpoint['protocol_sha256']!=sha(ASSETS/'protocol.json'):raise ValueError('Checkpoint protocol mismatch')
        model.load_state_dict(checkpoint['model']);epoch_best=checkpoint['epoch'];best=checkpoint['validation']['accuracy']
        if evaluate(model,val,cfg['eval_batch_size'],device)!=checkpoint['validation']:raise ValueError('Reload validation mismatch')
        ckpath=args.reload
    else:
        optimizer=torch.optim.Adam(model.parameters(),lr=cfg['lr'],weight_decay=cfg['weight_decay'])
        # Independent sampler: paired training order unaffected by model initialization or negative sampling.
        sampler=torch.Generator().manual_seed(args.seed)
        active=None
        for epoch in range(1,(1 if args.smoke else cfg['epochs'])+1):
            model.train();order=torch.randperm(len(train),generator=sampler).tolist();loss_sum=0.
            for i in range(0,len(order),cfg['batch_size']):
                sub=[train[j] for j in order[i:i+cfg['batch_size']]];graph,labels=collate(sub,device)
                optimizer.zero_grad(set_to_none=True);logits=model(graph)
                if logits.shape!=(len(labels),8) or not torch.isfinite(logits).all():raise ValueError('Invalid logits')
                loss=module.training_loss(logits,labels)
                if loss.ndim or not torch.isfinite(loss):raise ValueError('Invalid scalar loss')
                loss.backward()
                if active is None:
                    active=sum(p.numel() for p in model.parameters() if p.grad is not None)
                    provenance['parameters_with_gradient_first_batch']=active;write_json(args.output/'provenance.json',provenance)
                optimizer.step();loss_sum+=float(loss.detach())*len(sub)
            validation=evaluate(model,val,cfg['eval_batch_size'],device)
            if validation['accuracy']>best:
                best=validation['accuracy'];epoch_best=epoch
                torch.save(dict(model=model.state_dict(),epoch=epoch,validation=validation,seed=args.seed,
                                method_sha256=sha(args.method),protocol_sha256=sha(ASSETS/'protocol.json')),args.output/'best.pt')
            rec=dict(epoch=epoch,train_loss=loss_sum/len(train),validation=validation,best_epoch=epoch_best,elapsed_seconds=time.time()-start)
            with (args.output/'epochs.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
            print(json.dumps(rec),flush=True)
        ckpath=args.output/'best.pt';checkpoint=torch.load(ckpath,map_location=device);model.load_state_dict(checkpoint['model'])
        if evaluate(model,val,cfg['eval_batch_size'],device)!=checkpoint['validation']:raise ValueError('Checkpoint mismatch')
    tests=[]
    if not public_dev:
        for item in manifest['test_files']:
            test=read_rows(args.test_data/item['file'])
            record={**item,**evaluate(model,test,cfg['eval_batch_size'],device)};tests.append(record)
            write_json(args.output/'test-progress.json',tests);print('TEST',json.dumps(record),flush=True)
    ood=[r for r in tests if r['k']>=5]
    result=dict(status='smoke' if args.smoke else 'public-dev' if public_dev else 'complete',seed=args.seed,best_epoch=epoch_best,best_val_accuracy=best,
                public_validation_accuracy=checkpoint['validation']['accuracy'],
                all24_macro_accuracy=sum(r['accuracy'] for r in tests)/len(tests) if tests else None,
                ood15_macro_accuracy=sum(r['accuracy'] for r in ood)/len(ood) if ood else None,
                elapsed_seconds=time.time()-start,peak_gpu_bytes=torch.cuda.max_memory_allocated(),checkpoint_sha256=sha(ckpath),
                independent_reload=bool(args.reload),per_test=tests)
    write_json(args.output/'result.json',result);print('COMPLETE',json.dumps({k:v for k,v in result.items() if k!='per_test'}),flush=True)
if __name__=='__main__':main()
