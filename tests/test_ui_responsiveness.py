"""Deterministic burst tests: no game, network, or saved state."""
import sys, queue, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app

class Scheduler:
    def __init__(self): self.jobs={};self.serial=0
    def after(self,delay,callback):
        self.serial+=1;self.jobs[self.serial]=(delay,callback);return self.serial
    def after_cancel(self,job): self.jobs.pop(job,None)
    def flush(self):
        jobs=list(self.jobs.values());self.jobs.clear()
        for _,callback in jobs:callback()

class Responsiveness(unittest.TestCase):
    def test_typing_burst_has_one_render(self):
        root=Scheduler();calls=[]
        a=SimpleNamespace(root=root,state={'tab':'mobs'},render=lambda **kw:calls.append(kw))
        for _ in 'orange mushroom':app.App._debounce_mob_search(a)
        self.assertEqual(len(root.jobs),1);root.flush()
        self.assertEqual(calls,[{'keep_scroll':False}])
        app.App._debounce_mob_search(a);a.state['tab']='quests';root.flush()
        self.assertEqual(len(calls),1)

    def test_background_burst_yields_without_losing_order(self):
        root=Scheduler();received=[];q=queue.Queue()
        for n in range(40):q.put((received.append,n,None))
        a=SimpleNamespace(root=root,results=q,set_status=lambda *args:None)
        a._poll=lambda:app.App._poll(a)
        with patch.object(app.os.path,'exists',return_value=False):
            a._poll();self.assertGreater(q.qsize(),0)
            self.assertEqual(next(iter(root.jobs.values()))[0],10)
            while q.qsize():root.flush()
        self.assertEqual(received,list(range(40)))
        self.assertEqual(next(iter(root.jobs.values()))[0],100)

if __name__=='__main__':unittest.main()
