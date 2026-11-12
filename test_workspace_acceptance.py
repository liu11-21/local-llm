from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from workspace_acceptance import gpu_matches, host_diagnosis


class AcceptanceToolTests(unittest.TestCase):
    def test_missing_runtime_and_weights_never_launch_or_download(self):
        with TemporaryDirectory() as directory, patch('workspace_acceptance.subprocess.run') as launch:
            result=host_diagnosis(Path(directory),'NVIDIA GPU',[{'name':'Intel Iris Xe'}])
            self.assertFalse(gpu_matches(result['devices'],'RTX 5070 Ti'))
            self.assertEqual(result['torch']['status'],'NOT RUN')
            self.assertGreater(result['weights']['video']['needed'],8*1024**3)
            self.assertTrue(all(item['status']=='missing' for item in result['weights']['music']['files']))
            launch.assert_not_called()
            self.assertFalse(result['downloads_started'])
