import asyncio
from app.market_intelligence.streaming import MarketUpdate, StreamingDecisionEngine

async def main():
    async def decide(update,state):
        return {"event_id":update.event_id,"market":update.market,"odd":state.latest_odd,"movement_pct":state.delta_pct}
    engine=StreamingDecisionEngine(decide)
    await engine.publish(MarketUpdate("demo","football","league","book","1x2","home",2.10,source="demo"))
    await engine.publish(MarketUpdate("demo","football","league","book","1x2","home",2.00,source="demo"))
    print(await engine.process_once()); print(await engine.process_once()); print(engine.metrics.snapshot())
if __name__=='__main__': asyncio.run(main())
