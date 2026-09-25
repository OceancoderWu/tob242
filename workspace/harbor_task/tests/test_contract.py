"""Static preparation checks. No model training, GPU, or benchmark execution."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

TASK=Path(__file__).resolve().parents[1]
ROOT=TASK.parents[1] if len(TASK.parents)>1 else None
ASSETS=TASK/'environment/public_assets'
sys.path.insert(0,str(TASK/'tests'))
from score import score
from security import check_method

class PreparationContract(unittest.TestCase):
    def test_layout_and_edit_surface(self):
        self.assertEqual({p.name for p in (TASK/'solution').iterdir() if p.is_file()}, {'method.py','solve.sh'})
        self.assertEqual((TASK/'solution/method.py').read_bytes(),(TASK/'environment/starter/method.py').read_bytes())
        if ROOT is not None and (ROOT/'evaluation_assets').is_dir():
            self.assertTrue((ROOT/'workspace/reference/method.py').is_file())
        self.assertFalse((TASK/'reference').exists())
        self.assertNotIn('workspace/reference', (TASK/'environment/Dockerfile').read_text())
        check_method(TASK/'solution/method.py')

    def test_original_files_have_frozen_hashes(self):
        manifest=json.loads((ASSETS/'manifest.json').read_text())
        files=[manifest['train_file'],*manifest['test_files']]
        self.assertEqual(len(files),25)
        self.assertEqual(manifest['train_file']['rows'],57600)
        self.assertEqual(sum(x['rows'] for x in manifest['test_files']),153600)
        self.assertEqual({(x['k'],x['b']) for x in manifest['test_files']},{(k,b) for k in range(2,10) for b in range(1,4)})
        self.assertEqual({p.name for p in (ASSETS/'data').glob('*.csv')},{manifest['train_file']['file']})
        train=manifest['train_file'];path=ASSETS/'data'/train['file']
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),train['sha256'])
        if ROOT is not None and (ROOT/'evaluation_assets/data').is_dir():
            for item in manifest['test_files']:
                path=ROOT/'evaluation_assets/data'/item['file']
                self.assertTrue(path.is_file(),item['file'])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),item['sha256'],item['file'])

    def test_frozen_protocol_and_continuous_score(self):
        p=json.loads((ASSETS/'protocol.json').read_text())
        self.assertEqual(p['seeds'],[42,43,44])
        self.assertEqual((p['epochs'],p['batch_size'],p['eval_batch_size'],p['hidden_dim'],p['num_steps']),(40,128,128,32,9))
        self.assertEqual((p['optimizer'],p['lr'],p['weight_decay']),('Adam',0.01,0))
        self.assertEqual(score(0.4,0.4),0)
        self.assertLess(score(0.3,0.4),0)
        self.assertGreater(score(0.9,0.4),0.8)

if __name__=='__main__':unittest.main()
