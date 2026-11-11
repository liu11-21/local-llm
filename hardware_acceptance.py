"""Record actual device discovery and monitoring on a Windows acceptance machine."""
import argparse
import json
from pathlib import Path
from statistics import median
from time import monotonic, perf_counter, sleep

from hardware_contract import validate_hardware
from hardware_monitor import HardwareMonitor
from hardware_providers import probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--providers",action="store_true",help="Also initialize already-installed optional provider discovery APIs")
    args = parser.parse_args()
    monitor = HardwareMonitor()
    samples, durations = [],[]
    try:
        monitor.snapshot()
        deadline = monotonic()+25
        while monitor.refresh_thread and monitor.refresh_thread.is_alive() and monotonic()<deadline:
            sleep(0.25)
        for _ in range(3):
            sleep(3.2)
            started = perf_counter()
            samples.append(validate_hardware(monitor.snapshot()))
            durations.append(round((perf_counter()-started)*1000,2))
        if args.providers:
            monitor.set_providers(probe(),"checked")
        record = {"scope":"inventory-and-monitoring","status":"PASS" if samples[-1]["state"]=="available" else "NOT RUN",
                  "npu_inference":"NOT RUN","median_sample_ms":median(durations),"sample_ms":durations,
                  "samples":samples,"providers":monitor.snapshot()["providers"]}
        encoded = json.dumps(record,ensure_ascii=True,indent=2)
        if args.output:
            args.output.write_text(encoded+"\n",encoding="utf-8")
        print(encoded)
    finally:
        monitor.close()


if __name__=="__main__":
    main()
