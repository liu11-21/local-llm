from pathlib import Path
from tempfile import TemporaryDirectory
from time import time,monotonic,sleep
import unittest

from desktop_worker import Desktop
from runtime_provider import OpenAIProvider


class AgentDeviceTests(unittest.TestCase):
    def test_external_tools_require_plan_scoped_consent_and_tokens_stay_redacted(self):
        with TemporaryDirectory() as folder:
            app=Desktop(Path(folder))
            provider=OpenAIProvider('a'*32,'cloud','Controlled cloud','fixture.invalid',443,'/v1','test-private-key',['fixture'],True,int(time()))
            requests=[]
            def stream(model,messages,*_):
                requests.append((model,messages))
                yield 'answer test-private-key'
            provider.stream=stream
            app.providers.items[provider.id]=provider
            form={'role':'general','runtime':provider.id,'model':'fixture','tools':['models'],'mode':'simple','prompt':'Summarize the approved model list.','policy':'manual'}
            try:
                with self.assertRaises(ValueError):app.rpc('agent-plan',form)
                self.assertEqual(requests,[])
                plan=app.rpc('agent-plan',{**form,'consent':True})
                job=app.rpc('run',{'action':'agent','id':plan['id'],'version':plan['version'],'confirmed':True})
                end=monotonic()+5
                while monotonic()<end:
                    task=app.rpc('job',job)
                    if task['state'] not in ('running','queued'):break
                    sleep(.02)
                self.assertEqual(task['state'],'completed',task.get('error'))
                self.assertEqual(task['runtime'],provider.id)
                self.assertEqual(len(requests),1)
                self.assertIn('models',requests[0][1][-1]['content'])
                self.assertNotIn('test-private-key',task['result']['answer'])
                with self.assertRaises(ValueError):app.rpc('run',{'action':'agent','id':plan['id'],'version':plan['version'],'confirmed':True})
            finally:app.close()

    def test_native_tools_not_advertised_on_unsupported_runtime(self):
        from desktop_agent import create_plan
        with self.assertRaisesRegex(ValueError,'原生工具'):
            create_plan({'role':'general','runtime':'openvino','model':'model','prompt':'task','tools':[],'mode':'native'},None)


if __name__=='__main__':unittest.main()
