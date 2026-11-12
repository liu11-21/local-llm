from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from desktop_worker import Desktop
from resource_policy import memory_policy,GIB
from comfy_resources import reservation


class ResourceFinishTests(TestCase):
    def test_dynamic_limit_can_exceed_eight_gib_but_never_physical_or_user_cap(self):
        policy=memory_policy(32*GIB,24*GIB,required=12*GIB)
        self.assertTrue(policy['feasible']);self.assertEqual(policy['job_limit'],12*GIB)
        self.assertFalse(memory_policy(16*GIB,12*GIB,required=16*GIB)['feasible'])
        self.assertFalse(memory_policy(32*GIB,24*GIB,user_mib=8192,required=12*GIB)['feasible'])
        self.assertFalse(memory_policy(None,required=GIB)['feasible'])
        self.assertFalse(memory_policy(32*GIB,required=None)['feasible'])
        self.assertEqual(memory_policy(32*GIB,2*GIB)['admission_available'],0)

    def test_recommendation_receipt_revalidates_benchmark_and_identity(self):
        with TemporaryDirectory() as folder:
            app=Desktop(Path(folder))
            entry={'session':'benchmark','run':'run','condition_key':'same','freshness':'current','comparability':'partially_comparable','eligible_for_ranking':True}
            candidate={'id':'local|llama.cpp|CPU','runtime':'local','device':'CPU','executable':True,'identity':{'model_hashes':{'gguf':'original'}},'evidence':[entry]}
            result={'recommended':candidate['id'],'candidates':[candidate],'usage':{'reference_only':True},'objective':'latency'}
            try:
                with patch.object(app.device_recommendations,'query',return_value=result):
                    issued=app.recommendation_receipts.issue({'task':'chat','model':'fixture'})
                    receipt=app.recommendation_receipts.verify(issued['recommendation_id'],'local','CPU','fixture')
                self.assertEqual(receipt['benchmarks'][0]['benchmark_id'],'benchmark')
                for mutation in ('weights','driver','benchmark'):
                    changed=deepcopy(result)
                    if mutation=='benchmark':changed['candidates'][0]['evidence'][0]['eligible_for_ranking']=False
                    else:changed['candidates'][0]['identity'][mutation]='new'
                    with patch.object(app.device_recommendations,'query',return_value=changed),self.assertRaisesRegex(ValueError,'INVALIDATED'):
                        app.recommendation_receipts.verify(issued['recommendation_id'],'local','CPU','fixture')
                with patch('recommendation_receipts.time',return_value=10**12),self.assertRaisesRegex(ValueError,'EXPIRED'):
                    app.recommendation_receipts.verify(issued['recommendation_id'],'local','CPU','fixture')
            finally:app.close()

    def test_comfy_reliable_idle_dedicated_gpu_allows_cpu_but_busy_unknown_and_uma_are_global(self):
        reading=lambda n:{'value':n,'checked_at':100,'status':'available','source':'detected','unit':'bytes'}
        gpu={'id':'physical','kind':'gpu','name':'Test GPU','memory_type':'dedicated','vram_total':reading(8*GIB),'vram_available':reading(6*GIB)}
        stats={'devices':[{'name':'cuda:0 Test GPU','type':'cuda','vram_total':8*GIB,'vram_free':6*GIB,'torch_vram_total':GIB}]}
        queue={'queue_running':[],'queue_pending':[]}
        state,claim=reservation(stats,queue,{'devices':[gpu]},GIB,now=100)
        self.assertTrue(state['precise']);self.assertEqual(claim.exclusive,('gpu:physical',))
        for altered in ({'queue_running':[1],'queue_pending':[]},{}):
            state,claim=reservation(stats,altered,{'devices':[gpu]},GIB,now=100)
            self.assertFalse(state['precise']);self.assertEqual(claim.exclusive,('local:*',))
        gpu['memory_type']='unified'
        self.assertFalse(reservation(stats,queue,{'devices':[gpu]},GIB,now=100)[0]['precise'])
