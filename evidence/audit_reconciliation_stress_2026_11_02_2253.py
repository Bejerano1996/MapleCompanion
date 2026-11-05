from pathlib import Path
import sys,json,random,hashlib,time,tracemalloc,gc,statistics
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_accounting import NoticeReconciliation
rng=random.Random(2253);a=NoticeReconciliation();keys=set(a.__dict__);latencies=[]
def cycle(i):
 now=i*10.;old=rng.randint(1,500);fresh=rng.randint(1,100);covered=rng.randint(1,100)
 assert a.feed(dict(exp=old+covered,kills=1),covered,now)==old
 assert a.feed(dict(exp=fresh,kills=1),None,now+2)==old+fresh
 assert a.feed({},0,now+5)==old+fresh
 assert a.feed({},0,now+5.001)==fresh
 assert a.feed({},fresh,now+6)==0
 assert a.feed({},None,now+9)==0
 assert set(a.__dict__)==keys
for i in range(1000):cycle(i)
gc.collect();tracemalloc.start();before=tracemalloc.take_snapshot();started=time.perf_counter()
for i in range(1000,21000):
 start=time.perf_counter_ns();cycle(i)
 if i<2000:latencies.append((time.perf_counter_ns()-start)/6/1000)
elapsed=time.perf_counter()-started;gc.collect();after=tracemalloc.take_snapshot();current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
module_growth=sum(max(0,s.size_diff) for s in after.compare_to(before,'filename') if str(root/'training_accounting.py') in s.traceback[0].filename)
assert module_growth<65536,module_growth
assert a.pending==0 and a.base_pending==0 and a.stable_pending==0 and a.stable_at is None
report=dict(ok=True,cycles=20000,feed_calls=120000,elapsed_seconds=elapsed,module_retained_growth_bytes=module_growth,traced_peak_bytes=peak,fields=len(keys),sampled_call_microseconds_median=statistics.median(latencies),sampled_call_microseconds_p99=sorted(latencies)[989],source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic reconciliation-only stress, timing includes tracemalloc and cycle assertions; not OCR, fullapp latency or livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
