"""Runs inside the full derived image with no household endpoints or secrets."""
import asyncio,hashlib,json,logging,os,tempfile,types
from pathlib import Path
os.environ['DB_PATH']='/tmp/echomuse-smoke/controller.sqlite'
os.environ['HOUSEHOLD_EXTERNAL_HOLD_PATH']='/tmp/echomuse-smoke/holds.sqlite'
os.environ.pop('HOUSEHOLD_EXTERNAL_AUDIO_CONFIG',None)
Path('/tmp/echomuse-smoke').mkdir(parents=True,exist_ok=True)
logging.basicConfig(level=logging.WARNING)
import em_controller as controller
import em_esphome
import em_api
import em_auth
import em_db
import em_household_audio as external
from aiohttp.test_utils import TestClient,TestServer

class WS:
    def __init__(self):self.sent=[]
    async def send(self,data):self.sent.append(json.loads(data))
class Peer:
    def __init__(self):self.complete=False
    async def request(self,op,turn,url=''):
        return op!='play' or self.complete

async def main():
    em_db.init(os.environ["DB_PATH"])
    em_api.init({}, {}, {})
    app=await em_api.create_app()
    client=TestClient(TestServer(app));await client.start_server()
    ws=WS();device=controller.Device('SYNTHETIC-FIXTURE','127.0.0.1',[],ws)
    peer=Peer();store=external.DurableHold(os.environ['HOUSEHOLD_EXTERNAL_HOLD_PATH'])
    adapter=external.DeviceAudio(device,peer,store)
    external._devices[device.device_id]=adapter
    endpoint='/api/devices/SYNTHETIC-FIXTURE/external-audio/recover'
    try:
        # Actual generated controller class + complete dependency image.
        assert not await adapter.play('https://fixture.invalid/not-fetched')
        assert adapter.held() and device.oww_paused.is_set()
        ws.sent.clear()
        await device.mic_start();await device.mic_start_turn();await device.listen_ack(7)
        assert not any(m['type'] in ('mic_start','listen_ack') for m in ws.sent)
        restarted=external.DurableHold(os.environ['HOUSEHOLD_EXTERNAL_HOLD_PATH'])
        assert restarted.held(device.device_id)
        response=await client.post(endpoint,json={'confirm_external_output_stopped':True})
        assert response.status==401
        async def readonly(request):return {'role':'readonly','id':1,'username':'synthetic'}
        em_auth.resolve_session=readonly
        response=await client.post(endpoint,json={'confirm_external_output_stopped':True})
        assert response.status==403
        async def admin(request):return {'role':'admin','id':1,'username':'synthetic'}
        em_auth.resolve_session=admin
        response=await client.post(endpoint,json={});assert response.status==409
        response=await client.post(endpoint,json={'confirm_external_output_stopped':True})
        result=await response.json();assert response.status==200 and result['hold_cleared'] and result['playback_completion_proven'] is False
        assert not external.DurableHold(os.environ['HOUSEHOLD_EXTERNAL_HOLD_PATH']).held(device.device_id)
        assert any(m['type']=='mic_start' for m in ws.sent)
        peer.complete=True
        assert await adapter.play('https://fixture.invalid/not-fetched')
        assert not adapter.held()
        print(json.dumps({'result':'passed','full_upstream_imports':True,'real_controller_mic_gate':True,'persistent_hold_restart':True,'actual_admin_route_401_403_409_200':True,'success_releases_hold':True,'household_contacts':False,'physical_audio':False,'patched_sha256':{name:hashlib.sha256(Path('/app',name).read_bytes()).hexdigest() for name in ('em_controller.py','em_esphome.py','em_api.py','em_household_audio.py')}}))
    finally:
        await client.close()
asyncio.run(main())
