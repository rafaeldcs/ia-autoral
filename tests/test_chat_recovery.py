"""Real SQLite recovery, idempotency and lost-response/crash boundaries."""
import json
import threading
import time
import uuid
from contextlib import contextmanager

from localauthor.application import Application
from localauthor.errors import AccessDeniedError,ConflictError,NotFoundError,PolicyError
from localauthor.identity_context import current_actor,current_author,current_request
from tests.helpers import WorkspaceCase


class RecoveryTests(WorkspaceCase):
    def setUp(self):
        super().setUp();self.app=Application(self.settings)
        self.owner,_=self.app.identity.identify('Owner fixture',local=True)
        self.person,_=self.app.identity.identify('Person fixture',local=False)

    def tearDown(self):self.app.close();super().tearDown()

    @contextmanager
    def actor(self,user=None):
        user=user or self.owner;a=current_actor.set(user['id']);n=current_author.set(user['name'])
        try:yield
        finally:current_author.reset(n);current_actor.reset(a)

    def pending(self,conversation=None):
        return {'request_id':uuid.uuid4().hex,'conversation_id':conversation or uuid.uuid4().hex,'message':'Pending fixture','mode':'guide'}

    def submit(self,conversation,request_id=None,message='Como testar o projeto?'):
        return self.app.jobs.submit('chat',{'project_id':self.project['id'],'conversation_id':conversation,'message':message,'mode':'guide','input_format':'auto'},request_id=request_id or uuid.uuid4().hex)

    def wait(self,job):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            result=self.app.jobs.get(job['id'])
            if result['state'] not in ('queued','running'):return result
            time.sleep(.01)
        self.fail('Worker did not finish')

    def test_draft_roundtrip_tombstone_and_restart_preserve_code_exactly(self):
        text='const x = "ação";\n// </textarea><script>bad()</script>\n\\path 🛫'
        with self.actor():
            pending=self.pending();saved=self.app.recovery.save(self.project['id'],'',text,'foundation',0,pending)
            self.app.recovery.select(self.project['id'])
            self.assertEqual(saved['revision'],1)
        self.app.close();self.app=Application(self.settings)
        with self.actor():
            draft=self.app.recovery.draft(self.project['id'])
            self.assertEqual(draft['text'],text);self.assertEqual(draft['pending'],pending)
            self.assertEqual(self.app.recovery.workspace()['selection']['project_id'],self.project['id'])
            self.app.recovery.save(self.project['id'],'','','guide',1)
            with self.assertRaises(ConflictError):self.app.recovery.save(self.project['id'],'','stale','guide',1)
            self.assertEqual(self.app.recovery.draft(self.project['id'])['text'],'')

    def test_profiles_do_not_mix_drafts_even_inside_shared_conversation(self):
        self.app.identity.share(self.owner,self.project['id'],self.person['id'],'editor')
        with self.actor():
            conversation=self.app.chat.create(self.project['id'],'Shared')['id']
            self.app.recovery.save(self.project['id'],conversation,'Owner draft','guide',0)
        with self.actor(self.person):
            self.assertEqual(self.app.recovery.draft(self.project['id'],conversation)['text'],'')
            self.app.recovery.save(self.project['id'],conversation,'Person draft','foundation',0)
        with self.actor():self.assertEqual(self.app.recovery.draft(self.project['id'],conversation)['text'],'Owner draft')

    def test_revocation_hides_workspace_and_reader_cannot_save(self):
        self.app.identity.share(self.owner,self.project['id'],self.person['id'],'reader')
        with self.actor(self.person):
            self.app.recovery.select(self.project['id'])
            with self.assertRaises(AccessDeniedError):self.app.recovery.save(self.project['id'],'','x','guide',0)
        self.app.identity.share(self.owner,self.project['id'],self.person['id'],'none')
        with self.actor(self.person):
            self.assertIsNone(self.app.recovery.workspace()['selection'])
            with self.assertRaises(NotFoundError):self.app.recovery.draft(self.project['id'])

    def test_draft_conflict_and_invalid_pending_leave_original_intact(self):
        with self.actor():
            self.app.recovery.save(self.project['id'],'','original','guide',0)
            for mode,revision,pending in [('bad',1,None),('guide',True,None),('guide',1,{}),('guide',1,{'request_id':'bad','conversation_id':uuid.uuid4().hex})]:
                with self.assertRaises(PolicyError):self.app.recovery.save(self.project['id'],'','replacement',mode,revision,pending)
            with self.assertRaises(PolicyError):self.app.recovery.save(self.project['id'],'','x'*8001,'guide',1)
            with self.assertRaises(ConflictError):self.app.recovery.save(self.project['id'],'','other tab','guide',0)
            self.assertEqual(self.app.recovery.draft(self.project['id'])['text'],'original')

    def test_concurrent_draft_saves_have_one_winner(self):
        barrier=threading.Barrier(2);results=[]
        def save(text):
            with self.actor():
                barrier.wait()
                try:self.app.recovery.save(self.project['id'],'',text,'guide',0);results.append('saved')
                except ConflictError:results.append('conflict')
        workers=[threading.Thread(target=save,args=(text,)) for text in ('one','two')]
        for worker in workers:worker.start()
        for worker in workers:worker.join()
        self.assertCountEqual(results,['saved','conflict'])

    def test_repeated_conversation_creation_is_idempotent_and_scoped(self):
        ident=uuid.uuid4().hex
        with self.actor():
            first=self.app.chat.create(self.project['id'],'Original',ident=ident)
            again=self.app.chat.create(self.project['id'],'Retry',ident=ident)
            self.assertEqual(first,again);self.assertEqual(len(self.app.chat.conversations(self.project['id'])),1)
        self.app.identity.share(self.owner,self.project['id'],self.person['id'],'editor')
        with self.actor(self.person):
            with self.assertRaises(NotFoundError):self.app.chat.create(self.project['id'],'Other actor',ident=ident)

    def test_lost_response_retry_and_concurrent_submissions_create_one_job(self):
        with self.actor():conversation=self.app.chat.create(self.project['id'],'Only once')['id']
        ident=uuid.uuid4().hex;barrier=threading.Barrier(2);results=[]
        def submit():
            with self.actor():barrier.wait();results.append(self.submit(conversation,ident)['id'])
        workers=[threading.Thread(target=submit) for _ in range(2)]
        for worker in workers:worker.start()
        for worker in workers:worker.join()
        self.assertEqual(len(set(results)),1)
        with self.actor():
            with self.assertRaises(ConflictError):self.submit(conversation,ident,message='Changed content')
            self.app.start();result=self.wait({'id':results[0]});self.assertEqual(result['state'],'completed')
            recovered=self.app.recovery.request(self.project['id'],ident)
            self.assertEqual(recovered['state'],'completed');self.assertEqual(len(recovered['result']['messages']),2)
            self.assertEqual(self.submit(conversation,ident)['id'],results[0])
            self.assertEqual(len(self.app.chat.get(self.project['id'],conversation)['messages']),2)

    def test_commit_before_job_state_update_is_recovered_without_reexecution(self):
        with self.actor():
            conversation=self.app.chat.create(self.project['id'],'Crash boundary')['id'];ident=uuid.uuid4().hex
            job=self.submit(conversation,ident)
            token=current_request.set(ident)
            try:self.app.chat.respond(self.project['id'],conversation,'Como testar o projeto?')
            finally:current_request.reset(token)
        with self.app.store.connect() as db:db.execute("UPDATE jobs SET state='running' WHERE id=?",(job['id'],))
        self.app.close();self.app=Application(self.settings)
        with self.actor():
            self.assertEqual(self.app.jobs.get(job['id'])['state'],'interrupted')
            self.assertEqual(self.app.recovery.request(self.project['id'],ident)['state'],'completed')
            self.assertEqual(self.submit(conversation,ident)['id'],job['id'])
            self.assertEqual(len(self.app.chat.get(self.project['id'],conversation)['messages']),2)

    def test_unknown_interrupted_and_failed_requests_are_not_automatically_replayed(self):
        calls=[]
        def fails(payload,cancel):calls.append(payload['request_id']);raise PolicyError('Simulated failure after an external effect')
        self.app.jobs.handlers['chat']=fails
        with self.actor():
            with self.assertRaises(NotFoundError):self.app.recovery.request(self.project['id'],uuid.uuid4().hex)
            conversation=self.app.chat.create(self.project['id'],'No replay')['id'];ident=uuid.uuid4().hex
            job=self.submit(conversation,ident);self.app.start();self.assertEqual(self.wait(job)['state'],'failed')
            self.assertEqual(self.app.recovery.request(self.project['id'],ident)['state'],'failed')
            self.assertEqual(self.submit(conversation,ident)['id'],job['id']);self.assertEqual(calls,[ident])
        with self.actor(self.person):
            with self.assertRaises(NotFoundError):self.app.recovery.request(self.project['id'],ident)

    def test_memory_transaction_carries_request_receipt_without_repeating_memory(self):
        with self.actor():
            conversation=self.app.chat.create(self.project['id'],'Remember once')['id'];ident=uuid.uuid4().hex
            job=self.submit(conversation,ident,message='Lembre-se: prefiro exemplos curtos')
            self.app.start();self.assertEqual(self.wait(job)['state'],'completed')
            result=self.app.recovery.request(self.project['id'],ident)
            self.assertEqual(result['state'],'completed');self.assertEqual(result['result']['messages'][-1]['metadata']['request_id'],ident)
