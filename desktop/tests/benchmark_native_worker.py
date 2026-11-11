"""Native UI acceptance only: borrow the managed Runtime from another test profile."""
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import desktop_worker

Original = desktop_worker.Desktop


class NativeBenchmarkDesktop(Original):
    def __init__(self,data):
        super().__init__(data)
        self.openvino.runtime = Path(os.environ["LOCALLLM_BENCHMARK_RUNTIME"]).resolve()


desktop_worker.Desktop = NativeBenchmarkDesktop
if __name__=="__main__":
    desktop_worker.main()
