"""Opt-in external reply client. No credentials or household defaults in source."""
from __future__ import annotations
import asyncio
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
import secrets
import sqlite3
import time
from urllib.parse import urlsplit
import aiohttp

class ExternalAudioError(RuntimeError):
    pass

class Peer:
    def __init__(self, endpoint, key_id, key, *, timeout=65, session_factory=aiohttp.ClientSession):
        u=urlsplit(endpoint)
        if u.scheme != "https" or not u.netloc or u.username or u.password or u.query or u.fragment:
            raise ValueError("External audio requires an explicit HTTPS endpoint")
        if not isinstance(key,bytes) or len(key)<32 or not key_id:
            raise ValueError("External audio requires a scoped credential")
        self.endpoint,self.key_id,self.key=endpoint,key_id,key
        self.timeout,self.session_factory=timeout,session_factory
    async def request(self, operation, turn, media_url=""):
        nonce=secrets.token_hex(16)
        body=json.dumps({"version":1,"operation":operation,"turn":turn,
                         "media_url":media_url,"at":int(time.time()),
                         "nonce":nonce},sort_keys=True,separators=(",",":")).encode()
        signature=hmac.new(self.key,body,hashlib.sha256).hexdigest()
        try:
            async with self.session_factory(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(self.endpoint,data=body,allow_redirects=False,
                    headers={"Content-Type":"application/json","X-HV-Key":self.key_id,
                             "X-HV-Signature":signature}) as reply:
                    if reply.status!=200: raise ExternalAudioError("External audio rejected")
                    raw=bytearray()
                    while chunk:=await reply.content.read(min(1025-len(raw),512)):
                        raw.extend(chunk)
                        if len(raw)>1024: raise ExternalAudioError("Invalid external completion")
                    result=json.loads(raw)
                    if not isinstance(result,dict) or result.get("turn")!=turn:
                        raise ExternalAudioError("Invalid external completion")
                    if result.get('outcome')=='native':
                        signed=reply.headers.get('X-HV-Response-Signature','')
                        expected=hmac.new(self.key,b'response\0'+raw,hashlib.sha256).hexdigest()
                        if operation!='begin' or result.get('nonce')!=nonce or not hmac.compare_digest(expected,signed):
                            raise ExternalAudioError('Unauthenticated native disposition')
                        return 'native'
                    return result.get("outcome")=="completed"
        except asyncio.CancelledError:
            raise
        except Exception:
            raise ExternalAudioError("External audio unavailable or outcome unknown") from None

class DurableHold:
    """One controller-owned SQLite file: no keys, media URLs, or recordings."""
    def __init__(self,path):
        self.path=Path(path)
        if not self.path.is_absolute() or self.path.is_symlink() or any(p.is_symlink() for p in self.path.parents):
            raise ValueError("Explicit nonsymlink hold journal required")
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self._open() as db:
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0,1): raise ValueError("Unsupported hold journal")
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if version==0 and tables: raise ValueError("Unknown hold journal")
            if version==0:
                db.execute('CREATE TABLE holds (device TEXT PRIMARY KEY, reason TEXT NOT NULL)')
                db.execute('PRAGMA user_version=1')
            rows=db.execute('SELECT device,reason FROM holds').fetchall()
            if len(rows)>256 or any(not isinstance(d,str) or not 0<len(d)<=200 or r!='unconfirmed_playback' for d,r in rows):
                raise ValueError("Invalid hold journal")
        self.devices={d for d,_ in rows}
    @contextmanager
    def _open(self):
        if self.path.is_symlink(): raise ValueError("Symlink hold journal refused")
        db=sqlite3.connect(self.path,timeout=5)
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db: yield db
        finally: db.close()
    def held(self,device): return device in self.devices
    def hold(self,device):
        if not isinstance(device,str) or not 0<len(device)<=200: raise ValueError("Invalid device")
        self.devices.add(device)  # Fail closed in memory if durable write fails.
        with self._open() as db:
            if db.execute('SELECT COUNT(*) FROM holds').fetchone()[0]>=256 and not db.execute('SELECT 1 FROM holds WHERE device=?',(device,)).fetchone(): raise ValueError("Hold journal full")
            db.execute('INSERT OR REPLACE INTO holds VALUES (?,?)',(device,'unconfirmed_playback'))
    def clear(self,device):
        with self._open() as db: db.execute('DELETE FROM holds WHERE device=?',(device,))
        self.devices.discard(device)

class MemoryHold:
    """Fixture only; register() always supplies DurableHold."""
    def __init__(self): self.devices=set()
    def held(self,d): return d in self.devices
    def hold(self,d): self.devices.add(d)
    def clear(self,d): self.devices.discard(d)

class DeviceAudio:
    def __init__(self, device, peer, hold_store=None, *, enabled=True):
        self.device,self.peer=device,peer
        self.store=hold_store if hold_store is not None else MemoryHold()
        self.enabled=enabled is True
        self.lock=asyncio.Lock()
        self.turn=None
        self.native_turn=False
    def held(self): return self.store.held(self.device.device_id)
    async def begin_turn(self):
        async with self.lock:
            if self.held() or not self.enabled: return False
            if self.turn is not None: return True
            turn=secrets.token_hex(16)
            try:
                decision=await self.peer.request("begin",turn)
                if not decision:return False
            except ExternalAudioError: return False
            self.turn=turn
            self.native_turn=decision=='native'
            return True
    async def select_mode(self):
        if not await self.begin_turn():return 'blocked'
        if self.native_turn:
            await self.finish_turn()
            return 'native'
        return 'external'
    async def finish_turn(self):
        async with self.lock:
            turn,self.turn=self.turn,None
            if self.native_turn:
                self.native_turn=False
                return
            if turn is not None:
                try: await asyncio.wait_for(self.peer.request("end",turn),3)
                except (ExternalAudioError,TimeoutError): pass
    async def play(self,url,*,cancel=None):
        # No local fallback: a remote clip can outlive a disconnected HTTP request.
        async with self.lock:
            d=self.device
            if d.muted or d.cancel_event.is_set() or self.held() or not self.enabled or self.native_turn: return False
            turn=self.turn or secrets.token_hex(16)
            existing=self.turn is not None
            old_pause=d.oww_paused.is_set()
            d.oww_paused.set()
            request=None; watcher=None
            ok=False
            try:
                await d.mic_stop()
                if not existing and await self.peer.request("begin",turn) is not True: return False
                # Durable BEFORE handing the URL to a remote service. A process
                # death at any later point requires explicit operator recovery.
                await asyncio.to_thread(self.store.hold,d.device_id)
                _active[d.device_id]=_active.get(d.device_id,0)+1
                request=asyncio.create_task(self.peer.request("play",turn,url))
                async def cancelled():
                    while not d.cancel_event.is_set() and not d.muted and not (cancel and cancel()):
                        await asyncio.sleep(.025)
                watcher=asyncio.create_task(cancelled())
                done,_=await asyncio.wait({request,watcher},return_when=asyncio.FIRST_COMPLETED)
                if watcher in done:
                    request.cancel()
                    await asyncio.gather(request,return_exceptions=True)
                    return False
                ok=await request and not d.cancel_event.is_set() and not d.muted and not (cancel and cancel())
                if ok: await asyncio.to_thread(self.store.clear,d.device_id)
                return ok
            except (ExternalAudioError,sqlite3.Error,OSError,ValueError):
                return False
            finally:
                self.turn=None
                for task in (watcher,request):
                    if task and not task.done(): task.cancel()
                await asyncio.gather(*(t for t in (watcher,request) if t),return_exceptions=True)
                if request is not None:
                    _active[d.device_id]=max(0,_active.get(d.device_id,1)-1)
                try:
                    await asyncio.wait_for(self.peer.request("end" if ok else "cancel",turn),3)
                except (ExternalAudioError,TimeoutError): pass
                # Preserve the enclosing turn's wake ownership. Never unmute.
                if self.held():
                    d.oww_paused.set()
                    await d.mic_stop()
                elif not old_pause:
                    d.oww_paused.clear()
                    if not d.muted: await d.mic_start()
    async def announce(self,url,preannounce,reply,start=None):
        if not self.device.muted: self.device.cancel_event.clear()
        ok=False
        try:
            if preannounce and not await self.play(preannounce): return False
            ok=await self.play(url)
            return ok
        finally:
            reply(ok)
            if ok and start is not None and not self.device.muted and not self.held():
                await start()

    async def recover(self,*,operator_confirmed_stopped=False):
        if operator_confirmed_stopped is not True:
            raise ValueError("Operator must confirm external output has stopped")
        if self.lock.locked() or _active.get(self.device.device_id,0): raise ValueError("An external audio request is still active")
        async with self.lock:
            await asyncio.to_thread(self.store.clear,self.device.device_id)
            for name in ('mic_queue','voice_queue','listen_wakes'):
                queue=getattr(self.device,name,None)
                if queue is not None:
                    while not queue.empty():
                        try: queue.get_nowait()
                        except asyncio.QueueEmpty: break
            pending=getattr(self.device,'pending_wake',None)
            if pending is not None: pending.take()
            if not self.enabled and _devices.get(self.device.device_id) is self:
                _devices.pop(self.device.device_id,None)
            self.device.oww_paused.clear()
            self.device.oww_paused_since=None
            if not self.device.muted: await self.device.mic_start()
            return {"hold_cleared":True,"operator_confirmed_stopped":True,"playback_completion_proven":False}

_devices={}
_active={}

def load_configuration():
    """Read explicit protected override or native Supervisor add-on options."""
    path=os.environ.get('HOUSEHOLD_EXTERNAL_AUDIO_CONFIG')
    if path:
        return json.loads(Path(path).read_text(encoding='utf8'))
    options_path=Path('/data/options.json')
    if not options_path.exists():return {}
    options=json.loads(options_path.read_text(encoding='utf8'))
    enabled=options.get('external_audio_enabled',False)
    if type(enabled) is not bool:raise ValueError('Invalid external audio enabled setting')
    if not enabled:return {'enabled':False,'devices':{}}
    rows=options.get('external_audio_devices',[])
    if not isinstance(rows,list) or len(rows)>64:raise ValueError('Invalid external audio devices')
    devices={}
    for row in rows:
        if (not isinstance(row,dict) or set(row)!={'controller_device_id','endpoint','key_id','key_hex'}
                or not isinstance(row['controller_device_id'],str) or not re.fullmatch('[A-Za-z0-9_.:-]{1,128}',row['controller_device_id'])
                or row['controller_device_id'] in devices
                or not isinstance(row['key_id'],str) or not re.fullmatch('[a-f0-9]{32}',row['key_id'])
                or not isinstance(row['key_hex'],str) or not re.fullmatch('[a-f0-9]{64}',row['key_hex'])):
            raise ValueError('Invalid external audio registration')
        Peer(row['endpoint'],row['key_id'],bytes.fromhex(row['key_hex']))
        devices[row['controller_device_id']]={key:row[key] for key in ('endpoint','key_id','key_hex')}
    return {'enabled':True,'devices':devices}
def register(device):
    """Unconfigured means stock; persisted holds survive disabling the feature."""
    state_path=Path(os.environ.get("HOUSEHOLD_EXTERNAL_HOLD_PATH","/data/household-external-holds.sqlite3"))
    data=load_configuration()
    config=data.get("devices",{}).get(device.device_id)
    enabled=data.get("enabled") is True and config is not None
    _devices.pop(device.device_id,None)
    if not enabled and not state_path.exists(): return
    store=DurableHold(state_path)
    if not enabled and not store.held(device.device_id): return
    peer=Peer(config["endpoint"],config["key_id"],bytes.fromhex(config["key_hex"])) if enabled else None
    _devices[device.device_id]=DeviceAudio(device,peer,store,enabled=enabled)
    if store.held(device.device_id): device.oww_paused.set()
def get(device_id): return _devices.get(device_id)
def held(device_id):
    audio=get(device_id)
    return audio is not None and audio.held()
async def guard_listening(device):
    if not held(device.device_id): return False
    device.oww_paused.set()
    await device.mic_stop()
    # Drop already buffered audio; never score remote speech after recovery.
    for name in ('mic_queue','voice_queue','listen_wakes'):
        q=getattr(device,name,None)
        if q is not None:
            while not q.empty():
                try: q.get_nowait()
                except asyncio.QueueEmpty: break
    await asyncio.sleep(.25)
    return True
