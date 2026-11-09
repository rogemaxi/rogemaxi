"""Original preservation, ZIP security, invalid/corrupted uploads, secret redaction."""
import os, stat, sys, tempfile, unittest, zipfile, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent))
import fixtures
from engine import (import_product, inventory, original_file, safe_extract_zip, validate_zip, sha256,
                    verify_original)
from zipproject import WorkingCopy, PatchError, safe_relpath
from joblog import redact, JobLog


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        self.ws = self.d / 'ws'

    def tearDown(self):
        # originals are read-only; make removable on every OS
        for p in self.d.rglob('*'):
            try:
                os.chmod(p, stat.S_IWRITE | stat.S_IREAD | (stat.S_IEXEC if p.is_dir() else 0))
            except OSError:
                pass
        self.t.cleanup()

    def zip_with(self, name, entries, attr=None):
        p = self.d / name
        with zipfile.ZipFile(p, 'w') as z:
            for n, data in entries:
                info = zipfile.ZipInfo(n)
                if attr:
                    info.external_attr = attr
                z.writestr(info, data)
        return p


class ZipSecurity(Base):
    def assertRejected(self, p):
        with self.assertRaises(ValueError):
            safe_extract_zip(p, self.d / 'out')
        with self.assertRaises(ValueError):
            import_product(p, self.ws)
        self.assertEqual(inventory(self.ws), [], 'rejected import must leave no product behind')
        self.assertFalse((self.d / 'evil.txt').exists())

    def test_parent_traversal(self):
        self.assertRejected(self.zip_with('a.zip', [('../evil.txt', 'x')]))

    def test_nested_traversal(self):
        self.assertRejected(self.zip_with('b.zip', [('ok/../../evil.txt', 'x')]))

    def test_absolute_path(self):
        self.assertRejected(self.zip_with('c.zip', [('/tmp/evil.txt', 'x')]))

    def test_backslash_windows_traversal(self):
        self.assertRejected(self.zip_with('d.zip', [('..\\evil.txt', 'x')]))

    def test_drive_letter(self):
        self.assertRejected(self.zip_with('e.zip', [('C:/Windows/evil.txt', 'x')]))

    def test_symlink(self):
        self.assertRejected(self.zip_with('f.zip', [('link', '/etc/passwd')], attr=(0o120777 << 16)))

    def test_duplicate_entries(self):
        p = self.d / 'g.zip'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('index.html', 'a')
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                z.writestr('INDEX.html', 'b')
        self.assertRejected(p)

    def test_reserved_device_name(self):
        self.assertRejected(self.zip_with('h.zip', [('con.html', 'x')]))

    def test_too_many_entries(self):
        self.assertRejected(self.zip_with('i.zip', [(f'f{i}.txt', 'x') for i in range(501)]))

    def test_archive_bomb_ratio(self):
        p = self.d / 'bomb.zip'
        with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('big.txt', b'\0' * (20 * 1024 * 1024))
        self.assertRejected(p)

    def test_declared_size_lie_is_capped_while_streaming(self):
        p = self.d / 'lie.zip'
        with zipfile.ZipFile(p, 'w', zipfile.ZIP_STORED) as z:
            z.writestr('a.txt', b'A' * 5000)
        data = bytearray(p.read_bytes())
        # patch declared uncompressed size in central directory to 10 bytes
        cd = data.rfind(b'PK\x01\x02')
        data[cd + 24:cd + 28] = (10).to_bytes(4, 'little')
        lh = data.find(b'PK\x03\x04')
        data[lh + 22:lh + 26] = (10).to_bytes(4, 'little')
        p.write_bytes(bytes(data))
        with self.assertRaises(ValueError):
            safe_extract_zip(p, self.d / 'out')

    def test_corrupted_zip(self):
        p = self.d / 'corrupt.zip'
        p.write_bytes(b'PK\x03\x04 this is not a zip')
        self.assertRejected(p)

    def test_truncated_zip(self):
        z = fixtures.broken_power_tool_zip(self.d / 'ok.zip')
        p = self.d / 'trunc.zip'
        p.write_bytes(z.read_bytes()[:-60])
        self.assertRejected(p)

    def test_safe_relpath(self):
        for bad in ('../x', '/x', 'a\\b', 'C:/x', 'a/../../x'):
            with self.assertRaises(PatchError):
                safe_relpath(bad)
        self.assertEqual(safe_relpath('a/b.html'), 'a/b.html')


class InvalidUploads(Base):
    def test_unsupported_extension(self):
        p = self.d / 'x.exe'
        p.write_bytes(b'MZ')
        with self.assertRaises(ValueError):
            import_product(p, self.ws)

    def test_mislabeled_pdf(self):
        p = self.d / 'fake.pdf'
        p.write_text('<html>not a pdf</html>')
        with self.assertRaises(ValueError):
            import_product(p, self.ws)
        self.assertEqual(inventory(self.ws), [])

    def test_binary_in_text_file(self):
        p = self.d / 'x.html'
        p.write_bytes(b'\x00\x01\x02binary')
        with self.assertRaises(ValueError):
            import_product(p, self.ws)

    def test_empty_file(self):
        p = self.d / 'x.html'
        p.write_bytes(b'')
        with self.assertRaises(ValueError):
            import_product(p, self.ws)

    def test_corrupted_manifest_does_not_crash_inventory(self):
        z = fixtures.broken_power_tool_zip(self.d / 't.zip')
        m = import_product(z, self.ws)
        mf = self.ws / 'originals' / m['id'] / 'manifest.json'
        mf.write_text('{broken')
        inv = inventory(self.ws)
        self.assertEqual(inv[0]['status'], 'MANIFEST_CORRUPTED')

    def test_invalid_product_id(self):
        with self.assertRaises(ValueError):
            original_file(self.ws, '../../etc')


class Preservation(Base):
    def test_original_locked_and_fingerprinted(self):
        z = fixtures.broken_power_tool_zip(self.d / 't.zip')
        before = sha256(z)
        m = import_product(z, self.ws)
        src, _ = original_file(self.ws, m['id'])
        self.assertEqual(sha256(src), before)
        self.assertFalse(src.stat().st_mode & stat.S_IWUSR, 'original must be read-only')
        self.assertEqual(sha256(z), before, 'the owner\'s uploaded file itself is untouched')

    def test_tampered_original_detected(self):
        z = fixtures.broken_power_tool_zip(self.d / 't.zip')
        m = import_product(z, self.ws)
        src, _ = original_file(self.ws, m['id'])
        os.chmod(src, stat.S_IWRITE | stat.S_IREAD)
        with open(src, 'ab') as f:
            f.write(b'x')
        self.assertFalse(verify_original(self.ws, m['id']))
        with self.assertRaises(ValueError):
            original_file(self.ws, m['id'])

    def test_working_copy_isolated_and_rollback(self):
        z = fixtures.broken_power_tool_zip(self.d / 't.zip')
        m = import_product(z, self.ws)
        wc = WorkingCopy.create(self.ws, m['id'], 'job1')
        cp = wc.checkpoint('start')
        wc.apply_patch('quiz.js', 'answer: "54"', 'answer: "56"', 'fix')
        self.assertIn('answer: "56"', wc.read('quiz.js'))
        self.assertIn('-  {q: "What is 7 × 8?", answer: "54"}', wc.diff())
        self.assertEqual(wc.changed_files()['changed'], ['quiz.js'])
        wc.rollback(cp)
        self.assertEqual(wc.changed_files()['changed'], [])
        src, _ = original_file(self.ws, m['id'])
        self.assertEqual(sha256(src), m['sha256'])

    def test_patch_rules(self):
        z = fixtures.broken_power_tool_zip(self.d / 't.zip')
        m = import_product(z, self.ws)
        wc = WorkingCopy.create(self.ws, m['id'], 'job2')
        with self.assertRaises(PatchError):
            wc.apply_patch('quiz.js', 'answer', 'x', 'ambiguous')            # occurs more than once
        with self.assertRaises(PatchError):
            wc.apply_patch('images/logo.png', 'a', 'b', 'binary protected')
        with self.assertRaises(PatchError):
            wc.apply_patch('../outside.js', 'a', 'b', 'escape')
        with self.assertRaises(PatchError):
            wc.apply_patch('quiz.js', 'not present', 'b', 'missing')

    def test_repack_is_valid_and_deterministic(self):
        z = fixtures.broken_power_tool_zip(self.d / 't.zip')
        m = import_product(z, self.ws)
        wc = WorkingCopy.create(self.ws, m['id'], 'job3')
        a = wc.repack(self.d / 'a.zip')
        b = wc.repack(self.d / 'b.zip')
        self.assertEqual(sha256(a), sha256(b))
        validate_zip(a)


class Secrets(unittest.TestCase):
    def test_redaction(self):
        s = redact('key sk-proj-ABCDEFGHIJKLMNOPQRSTUV and api_key="supersecretvalue123"')
        self.assertNotIn('ABCDEFGHIJ', s)
        self.assertNotIn('supersecretvalue123', s)
        self.assertEqual(redact({'OPENAI_API_KEY': 'sk-abcdefghijklmnop'})['OPENAI_API_KEY'], '[REDACTED]')

    def test_job_log_never_contains_key(self):
        with tempfile.TemporaryDirectory() as t:
            JobLog(t, 'j').info('Orchestrator', 'using sk-live-1234567890abcdefXYZ', key='sk-live-1234567890abcdefXYZ')
            text = (Path(t) / 'logs' / 'job_j.jsonl').read_text()
            self.assertNotIn('1234567890abcdef', text)

    def test_no_hardcoded_keys_in_source(self):
        import re
        root = Path(__file__).parent.parent
        for p in root.rglob('*.py'):
            if 'tests' in p.parts:
                continue
            self.assertIsNone(re.search(r'sk-[A-Za-z0-9]{20,}', p.read_text(encoding='utf-8')), p)


if __name__ == '__main__':
    unittest.main()
