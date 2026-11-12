"""Local recommendation receipts join existing Benchmark and dispatch records."""
import json
from time import time
from uuid import uuid4


class RecommendationReceipts:
    def __init__(self,app):
        self.app=app
        with app.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS recommendation_receipts(id TEXT PRIMARY KEY,created REAL NOT NULL,request TEXT NOT NULL,result TEXT NOT NULL)')
            if db.execute('PRAGMA user_version').fetchone()[0]<13:db.execute('PRAGMA user_version=13')

    def issue(self,data):
        request={key:value for key,value in data.items() if key in
                 ('task','model','policy','preference','objective','workload','reference','context','max_tokens','memory_mib','batch','temperature','workload_sha256')}
        result=self.app.device_recommendations.query(request)
        identity=uuid4().hex
        with self.app.connect() as db:
            db.execute('INSERT INTO recommendation_receipts VALUES(?,?,?,?)',(identity,time(),json.dumps(request),json.dumps(result)))
        return {**result,'recommendation_id':identity}

    def verify(self,identity,runtime,device,model):
        with self.app.connect() as db:
            row=db.execute('SELECT created,request,result FROM recommendation_receipts WHERE id=?',(identity,)).fetchone()
        if not row or not 0<=time()-row[0]<=900:raise ValueError('RECOMMENDATION_EXPIRED · 請重新檢查並採用運算建議。')
        request,previous=json.loads(row[1]),json.loads(row[2])
        if request.get('model')!=model:raise ValueError('RECOMMENDATION_MODEL_CHANGED')
        key=previous.get('recommended')
        old=next((item for item in previous['candidates'] if item['id']==key),None)
        if not old or (old['runtime'],old['device'])!=(runtime,device):raise ValueError('RECOMMENDATION_SELECTION_CHANGED')
        current=self.app.device_recommendations.query(request)
        chosen=next((item for item in current['candidates'] if item['id']==key),None)
        if not chosen or not chosen['executable'] or current['recommended']!=key or old['identity']!=chosen['identity']:
            # Live RAM readings are not identity: compare stable values below.
            if not chosen or not chosen['executable'] or current['recommended']!=key:
                raise ValueError('RECOMMENDATION_INVALIDATED · 證據或可用設備已變更，請重新確認。')
        stable=lambda item:{k:v for k,v in item['identity'].items() if k!='resources'}
        if stable(old)!=stable(chosen):raise ValueError('RECOMMENDATION_INVALIDATED · 模型、引擎、驅動或設備已變更。')
        refs=[{'benchmark_id':entry['session'],'benchmark_run_id':entry['run'],'condition_key':entry['condition_key'],
               'freshness':entry['freshness'],'comparability':entry['comparability']} for entry in old['evidence'] if entry['eligible_for_ranking']][:1]
        current_refs={(entry['session'],entry['run'],entry['condition_key']) for entry in chosen['evidence'] if entry['eligible_for_ranking']}
        if any((ref['benchmark_id'],ref['benchmark_run_id'],ref['condition_key']) not in current_refs for ref in refs):
            raise ValueError('BENCHMARK_INVALIDATED · 原推薦的 Benchmark 已失效。')
        return {'recommendation_id':identity,'candidate':key,'benchmarks':refs,'usage':previous['usage'],
                'objective':previous['objective'],'reference_only':bool(previous.get('usage',{}).get('reference_only')),
                'actual_prompt_is_benchmark':False}
