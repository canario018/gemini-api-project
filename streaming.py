from __future__ import annotations
import asyncio, hashlib, json, time, uuid
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Any, Awaitable, Callable, Mapping

@dataclass(frozen=True)
class MarketUpdate:
    event_id: str
    sport: str
    league: str
    bookmaker: str
    market: str
    selection: str
    odd: float
    timestamp: float = field(default_factory=time.time)
    line: float | None = None
    source: str = ""
    sequence: int | None = None
    update_id: str | None = None

    def key(self) -> str:
        return f"{self.event_id}|{self.bookmaker}|{self.market}|{self.selection}|{self.line}"
    def fingerprint(self) -> str:
        payload = {"key": self.key(), "odd": self.odd, "sequence": self.sequence, "timestamp": self.timestamp, "source": self.source}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()

@dataclass
class MarketState:
    key: str
    latest_odd: float
    previous_odd: float | None
    first_odd: float
    min_odd: float
    max_odd: float
    updates: int
    first_timestamp: float
    last_timestamp: float
    delta: float
    delta_pct: float
    velocity_per_minute: float
    source: str = ""

class MarketStateStore:
    def __init__(self): self._states: dict[str, MarketState] = {}; self._seen: set[str] = set(); self._lock = asyncio.Lock()
    async def apply(self, u: MarketUpdate) -> tuple[MarketState, bool]:
        fp = u.update_id or u.fingerprint()
        async with self._lock:
            if fp in self._seen: return self._states[u.key()], False
            self._seen.add(fp)
            old = self._states.get(u.key())
            if old is None:
                state = MarketState(u.key(),u.odd,None,u.odd,u.odd,u.odd,1,u.timestamp,u.timestamp,0.0,0.0,0.0,u.source)
            else:
                elapsed=max(1e-6,u.timestamp-old.last_timestamp); delta=u.odd-old.latest_odd
                state=MarketState(u.key(),u.odd,old.latest_odd,old.first_odd,min(old.min_odd,u.odd),max(old.max_odd,u.odd),old.updates+1,old.first_timestamp,u.timestamp,delta,delta/old.latest_odd*100 if old.latest_odd else 0.0,delta/(elapsed/60),u.source or old.source)
            self._states[u.key()]=state
            return state, True
    async def get(self,key):
        async with self._lock:return self._states.get(key)

@dataclass(frozen=True)
class StreamDecision:
    action: str
    score: float
    reason: str
    event_id: str
    market_key: str
    prediction: Any = None
    created_at: float = field(default_factory=time.time)

class EventPriority:
    @staticmethod
    def score(u: MarketUpdate, state: MarketState | None = None) -> float:
        movement=abs(state.delta_pct) if state else 0.0
        freshness=max(0.0,1.0-(time.time()-u.timestamp)/300.0)
        return min(100.0, movement*10 + freshness*20)

class PriorityEventQueue:
    def __init__(self,maxsize=10000): self.queue=asyncio.PriorityQueue(maxsize=maxsize); self._counter=0
    async def put(self,u: MarketUpdate, priority: float):
        self._counter+=1
        await self.queue.put((-priority,self._counter,u))
    async def get(self): return (await self.queue.get())[2]
    def task_done(self): self.queue.task_done()
    def qsize(self): return self.queue.qsize()

class CircuitBreaker:
    def __init__(self,failure_threshold=5,recovery_seconds=30): self.failure_threshold=failure_threshold;self.recovery_seconds=recovery_seconds;self.failures=0;self.opened_at=None
    @property
    def open(self): return self.opened_at is not None and time.monotonic()-self.opened_at < self.recovery_seconds
    def allow(self):
        if self.open:return False
        if self.opened_at is not None:self.opened_at=None;self.failures=0
        return True
    def success(self): self.failures=0;self.opened_at=None
    def failure(self):
        self.failures+=1
        if self.failures>=self.failure_threshold:self.opened_at=time.monotonic()

@dataclass
class StreamingMetrics:
    received:int=0;processed:int=0;deduplicated:int=0;errors:int=0;decisions:int=0;total_latency_ms:float=0.0;max_latency_ms:float=0.0
    def observe(self,lat): self.processed+=1;self.total_latency_ms+=lat;self.max_latency_ms=max(self.max_latency_ms,lat)
    def snapshot(self): return {"received":self.received,"processed":self.processed,"deduplicated":self.deduplicated,"errors":self.errors,"decisions":self.decisions,"avg_latency_ms":self.total_latency_ms/self.processed if self.processed else 0.0,"max_latency_ms":self.max_latency_ms}

class StreamingDecisionEngine:
    """Stateful real-time market processor. Decision function is injected to preserve domain/model boundaries."""
    def __init__(self, decision_fn: Callable[[MarketUpdate,MarketState],Awaitable[Any]]|None=None, max_queue=10000, latency_sla_ms=250):
        self.states=MarketStateStore(); self.queue=PriorityEventQueue(max_queue); self.decision_fn=decision_fn; self.latency_sla_ms=latency_sla_ms; self.breaker=CircuitBreaker(); self.metrics=StreamingMetrics()
    async def publish(self,u:MarketUpdate):
        self.metrics.received+=1
        old=await self.states.get(u.key()); priority=EventPriority.score(u,old); await self.queue.put(u,priority)
    async def process_once(self):
        u=await self.queue.get(); start=time.perf_counter()
        try:
            state,accepted=await self.states.apply(u)
            if not accepted:
                self.metrics.deduplicated+=1; return None
            if not self.breaker.allow(): return StreamDecision("NO_ACTION",0.0,"circuit_breaker_open",u.event_id,u.key())
            prediction=None
            if self.decision_fn: prediction=await self.decision_fn(u,state)
            action="EVALUATE" if prediction is not None else "STATE_UPDATED"
            self.metrics.decisions+=int(prediction is not None)
            result=StreamDecision(action,EventPriority.score(u,state),"market_update_processed",u.event_id,u.key(),prediction)
            self.breaker.success(); return result
        except Exception as exc:
            self.metrics.errors+=1; self.breaker.failure(); raise exc
        finally:
            lat=(time.perf_counter()-start)*1000; self.metrics.observe(lat); self.queue.task_done()
    async def run(self,stop:asyncio.Event|None=None):
        while stop is None or not stop.is_set(): await self.process_once()
