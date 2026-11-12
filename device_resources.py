"""Atomic resource admission used by TaskManager, not a second queue."""
from dataclasses import asdict,dataclass


@dataclass(frozen=True)
class ResourceDemand:
    scope: str = "local"
    device: str = "legacy"
    engine: str = "legacy"
    ram: int = 0
    vram: tuple = ()  # (physical pool id, estimated bytes), never sums distinct GPUs
    shared_memory: int = 0  # already included in ram
    cpu_load: int = 0
    bandwidth: int = 0
    exclusive: tuple = ("local:*",)
    seconds: int = 600
    limitations: tuple = ()

    def __post_init__(self):
        if any(not isinstance(value,str) or not value or len(value)>300 for value in (self.device,self.engine)):
            raise ValueError('裝置與引擎識別必須為有效文字。')
        if self.scope not in ("local","remote","control") or any(type(value) is not int or value<0 for value in
                (self.ram,self.shared_memory,self.cpu_load,self.bandwidth,self.seconds)):
            raise ValueError("排程資源需求無效。")
        if self.shared_memory>self.ram or self.cpu_load>100 or self.bandwidth>100 or not 1<=self.seconds<=3600:
            raise ValueError("排程預算超出範圍。")
        if len(self.vram)>4 or any(not isinstance(pool,str) or type(size) is not int or size<0 for pool,size in self.vram):
            raise ValueError("顯存池預算無效。")

    def public(self):
        return asdict(self)


def conflicts(left,right):
    if left.scope!=right.scope or left.scope=="control":return False
    if "local:*" in left.exclusive or "local:*" in right.exclusive:return True
    for first in left.exclusive:
        for second in right.exclusive:
            if first==second or first.endswith("*") and second.startswith(first[:-1]) or second.endswith("*") and first.startswith(second[:-1]):
                return True
    return False


def admission(demand, running, snapshot):
    for identity,other in running:
        if conflicts(demand,other):return False,"RESOURCE_LOCK · 等候 "+identity
    if demand.scope!="local":return True,None
    local=[other for _,other in running if other.scope=="local"]
    if demand.ram:
        free=snapshot.get("ram_available")
        if free is None:return False,"RAM_UNKNOWN · 系統 RAM 可用量未知，等待可靠取樣。"
        if demand.ram+sum(item.ram for item in local)>free:
            return False,"RAM_BUDGET · 等候系統 RAM 預算釋放。"
    for pool,size in demand.vram:
        free=snapshot.get("vram",{}).get(pool)
        if free is None:return False,"VRAM_UNKNOWN · 所選裝置的可用專用顯存未知。"
        used=sum(amount for item in local for identity,amount in item.vram if identity==pool)
        if size+used>free:return False,"VRAM_BUDGET · 等候所選單張 GPU 顯存預算釋放。"
    if demand.cpu_load+sum(item.cpu_load for item in local)>100:
        return False,"CPU_BUDGET · 等候 CPU 負載預算。"
    if demand.bandwidth+sum(item.bandwidth for item in local)>100:
        return False,"SHARED_BANDWIDTH · 共享記憶體頻寬採保守排隊。"
    return True,None
