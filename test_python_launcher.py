"""Mock selection policy plus real installed-interpreter/CMD checks; no installs."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent


@unittest.skipUnless(os.name=='nt','Windows CMD/PowerShell selector')
class PythonLauncherTests(unittest.TestCase):
    def selection(self,candidates,versions=None,failed=(),space=False):
        lines=(ROOT/'Find-Web-Python.cmd').read_text().splitlines()
        parts=[re.fullmatch(r' "(.*)"(?: \^)?',line) for line in lines]
        script=' '.join(match[1] for match in parts if match and not match[1].startswith('try { Write-Output'))
        with tempfile.TemporaryDirectory(prefix='python selection with spaces ') as folder:
            exe=Path(folder)/'python.exe' if space else Path(sys.executable)
            if space:exe.write_bytes(b'never executed; mock probe only')
            literal=str(exe).replace("'","''")
            script+=";function Get-PythonCandidates { "+';'.join("[pscustomobject]@{exe='"+literal+"';prefix='"+prefix+"';source='"+source+"'}" for source,prefix in candidates)+" };"
            table={'key:'+prefix:[str(exe),version,bits] for prefix,(version,bits) in (versions or {}).items()}
            default=[str(exe),[3,12,10],64]
            setup=json.dumps({'values':table,'default':default,'failed':list(failed)},ensure_ascii=True).replace("'","''")
            script+="$global:fixture='"+setup+"'|ConvertFrom-Json; function Probe-Python($exe,$prefix) { if($global:fixture.failed -contains $prefix){throw 'controlled unavailable'}; $p=$global:fixture.values.PSObject.Properties[('key:'+$prefix)]; if($p){return ,$p.Value}; return ,$global:fixture.default };"
            script+="try { $p=Select-WebPython; Write-Output ('RESULT:'+ $p) } catch { Write-Output ('REJECT:'+ $_.Exception.Message) }"
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],text=True,capture_output=True,encoding='utf-8',errors='replace',timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            return result.stdout,result.stderr

    def test_launcher_python_312(self):self.assertIn('RESULT:',self.selection([('launcher','-3.12')])[0])
    def test_failed_launcher_then_path(self):
        out,err=self.selection([('launcher','-3.12'),('PATH','')],failed=['-3.12']);self.assertIn('RESULT:',out);self.assertIn('PATH',err)
    def test_registry_without_path(self):self.assertIn('registry',self.selection([('registry','')])[1])
    def test_multiple_versions(self):
        out,err=self.selection([('PATH','-old'),('registry','')],{'-old':([3,11,9],64)});self.assertIn('RESULT:',out);self.assertIn('rejected',err)
    def test_wrong_version_rejected(self):self.assertIn('REJECT:',self.selection([('PATH','')],{'':([3,13,0],64)})[0])
    def test_32_bit_rejected(self):self.assertIn('REJECT:',self.selection([('PATH','')],{'':([3,12,10],32)})[0])
    def test_spaces_in_install_path(self):self.assertIn('python selection with spaces ',self.selection([('registry','')],space=True)[0])
    def test_missing_python_has_installation_guidance(self):self.assertIn('https://www.python.org/downloads/windows/',self.selection([])[0])

    def test_real_finder_returns_verified_absolute_python(self):
        result=subprocess.run(['cmd.exe','/d','/c',str(ROOT/'Find-Web-Python.cmd')],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        path=Path(result.stdout.strip());self.assertTrue(path.is_absolute());self.assertTrue(path.is_file())
        value=json.loads(subprocess.check_output([str(path),'-I','-S','-B','-c','import sys,json,struct;print(json.dumps([list(sys.version_info[:2]),struct.calcsize("P")]))'],text=True))
        self.assertEqual(value,[[3,12],8])


if __name__=='__main__':unittest.main()
