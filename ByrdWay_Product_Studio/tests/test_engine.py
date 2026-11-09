import tempfile,unittest,zipfile
from pathlib import Path
from engine import import_product,original_file,create_audit,save_proposal,approve_proposal,safe_extract_zip,Budget
class Tests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);self.src=self.root/'sample.html';self.src.write_text('<h1>ByrdWay</h1><p>2+2=4</p>')
 def tearDown(self):self.t.cleanup()
 def test_import_hash_and_audit(self):
  m=import_product(self.src,self.root/'work');s,_=original_file(self.root/'work',m['id']);self.assertEqual(s.read_text(),self.src.read_text());r=create_audit(self.root/'work',m['id']);self.assertEqual(r['quality_score'],'NOT_MEASURED')
 def test_proposal_preserves_original(self):
  m=import_product(self.src,self.root/'work');r=save_proposal(self.root/'work',m['id'],'<p>2+2=4</p>','cleanup');s,_=original_file(self.root/'work',m['id']);self.assertIn('<h1>',s.read_text())
  with self.assertRaises(PermissionError):approve_proposal(self.root/'work',m['id'],r['candidate'])
  approved=approve_proposal(self.root/'work',m['id'],r['candidate'],True);self.assertTrue(approved.exists());self.assertIn('<h1>',s.read_text())
 def test_zip_traversal_blocked(self):
  z=self.root/'bad.zip'
  with zipfile.ZipFile(z,'w') as f:f.writestr('../evil.txt','bad')
  with self.assertRaises(ValueError):safe_extract_zip(z,self.root/'dest')
 def test_budget_stops(self):
  b=Budget(.5,3);self.assertFalse(b.can_continue(3,.1));self.assertFalse(b.can_continue(1,.5))
if __name__=='__main__':unittest.main()
