import unittest,tempfile,os,json,importlib.util,sys
from pathlib import Path
from unittest.mock import patch,MagicMock
import launch
class LaunchTests(unittest.TestCase):
 def test_relative_paths_resolved_before_chdir(self):
  before=Path.cwd()
  try:
   with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'BUS_DATA_PATH':'input.csv','BUS_MODEL_DIR':''}),patch('agent.catalog',return_value={'rows':1}):
    os.chdir(temp);launch.prepare_environment();self.assertEqual(os.environ['BUS_DATA_PATH'],str(Path(temp)/'input.csv'))
  finally:os.chdir(before)
 def test_default_port_conflict_moves_to_new_bound_port(self):
  sentinel=object()
  with patch('launch.ThreadingHTTPServer',side_effect=[OSError('busy'),sentinel]) as create:
   self.assertIs(launch.create_server(object()),sentinel)
   self.assertEqual([c.args[0] for c in create.call_args_list],[('127.0.0.1',8765),('127.0.0.1',8766)])
 def test_explicit_port_conflict_never_opens_other_server(self):
  with patch('launch.ThreadingHTTPServer',side_effect=OSError('busy')):
   with self.assertRaisesRegex(OSError,'지정 포트'):launch.create_server(object(),8765)
 def test_invalid_port(self):
  for value in ['abc',-1,65536]:
   with self.assertRaises(ValueError):launch.create_server(object(),value)
 def test_browser_waits_for_matching_source(self):
  response=MagicMock();response.__enter__.return_value=response;response.read.return_value=json.dumps({'sha256':'verified'}).encode()
  with patch('launch.urlopen',return_value=response),patch('launch.webbrowser.open',return_value=True) as opened:
   launch.open_browser('http://127.0.0.1:1234','verified');opened.assert_called_once_with('http://127.0.0.1:1234',new=2)
 def test_browser_not_opened_on_mismatched_server(self):
  response=MagicMock();response.__enter__.return_value=response;response.read.return_value=json.dumps({'sha256':'wrong'}).encode()
  with patch('launch.urlopen',return_value=response),patch('launch.time.sleep'),patch('launch.webbrowser.open') as opened:
   launch.open_browser('http://127.0.0.1:1234','verified');opened.assert_not_called()
 def test_missing_model_friendly_error(self):
  before=Path.cwd()
  try:
   with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'BUS_MODEL_DIR':temp,'BUS_DATA_PATH':str(Path(temp)/'source.csv')}):
    with self.assertRaisesRegex(ValueError,'AI 모델이 없습니다'):launch.prepare_environment()
  finally:os.chdir(before)
 def test_download_destination_project_relative(self):
  script=Path(launch.__file__).parent/'scripts/download_model.py'
  spec=importlib.util.spec_from_file_location('download_model_test',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  stub=MagicMock()
  with patch.dict(sys.modules,{'huggingface_hub':stub}),patch('builtins.print'):module.main()
  self.assertEqual(stub.snapshot_download.call_args.kwargs['local_dir'],str(Path(launch.__file__).parent/'models/qwen15'))
  self.assertEqual(stub.snapshot_download.call_args.kwargs['revision'],'989aa7980e4cf806f80c7fef2b1adb7bc71aa306')
 def test_loopback_readiness_ignores_environment_proxy(self):
  from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
  import threading
  class Handler(BaseHTTPRequestHandler):
   def do_GET(self):
    body=b'{"sha256":"verified"}'
    self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
   def log_message(self,*args):pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with patch.dict(os.environ,{'HTTP_PROXY':'http://127.0.0.1:9','http_proxy':'http://127.0.0.1:9','NO_PROXY':'','no_proxy':''}),patch('launch.webbrowser.open',return_value=True) as opened:
    launch.open_browser(f'http://127.0.0.1:{server.server_port}','verified')
    opened.assert_called_once()
  finally:server.shutdown();server.server_close()
