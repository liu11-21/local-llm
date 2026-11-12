"""Record controlled protocol/transport checks separately from real model inference."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import unittest
from registries import media_metadata


class Recorded(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.cases=[]
    def addSuccess(self,test):super().addSuccess(test);self.cases.append({'test':test.id(),'status':'PASS'})
    def addFailure(self,test,error):super().addFailure(test,error);self.cases.append({'test':test.id(),'status':'FAIL'})
    def addError(self,test,error):super().addError(test,error);self.cases.append({'test':test.id(),'status':'FAIL'})
    def addSkip(self,test,reason):super().addSkip(test,reason);self.cases.append({'test':test.id(),'status':'NOT RUN','reason':reason})


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromNames(['test_remote_media','test_media_contract','test_remote_video','test_remote_audio','test_remote_retention','test_media_previews','test_resource_finish'])
    result=unittest.TextTestRunner(verbosity=1,resultclass=Recorded).run(suite)
    root=Path(__file__).parent/'desktop/tests/media-fixtures'
    fixtures=[{'name':path.name,'bytes':path.stat().st_size,'sha256':sha256(path.read_bytes()).hexdigest(),'metadata':media_metadata(path)} for path in root.glob('sample.*')]
    record={'status':'PASS' if result.wasSuccessful() else 'FAIL','model_inference':False,'transport':'production Host/Client/storage paths, controlled inference and legal encoded media',
        'tls':'verified separately on clean Windows CI','cases':result.cases,'fixtures':fixtures,'large_video_void_padding_bytes':34*1024**2,
        'client_staging_quota_bytes':4*1024**3,'host_storage_quota_bytes':8*1024**3,'thumbnail_cache_limit_bytes':16*1024**2,'host_retention_days':7}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return not result.wasSuccessful()


if __name__=='__main__':raise SystemExit(main())
