from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EditorLimitTests(unittest.TestCase):
    def read(self, root, file):
        return subprocess.run([sys.executable,str(ROOT/'plogical/safeFileRead.py'),
                               '--allowed-root',str(root),'--file',str(file)],
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)

    def test_boundary_and_large_file_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); file=root/'log.txt'
            file.write_bytes(b'x'*(4*1024*1024))
            result=self.read(root,file)
            self.assertEqual(0,result.returncode)
            self.assertEqual(4*1024*1024,len(result.stdout))
            with file.open('ab') as handle: handle.write(b'x')
            result=self.read(root,file)
            self.assertNotEqual(0,result.returncode)
            self.assertEqual(b'CYBERPANEL_FILE_TOO_LARGE\n',result.stdout)
            self.assertEqual(b'',result.stderr)

    def test_symlink_and_outside_paths_stay_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); root=base/'allowed';root.mkdir()
            outside=base/'private';outside.write_text('private-marker')
            link=root/'link';link.symlink_to(outside)
            for file in (link,outside):
                result=self.read(root,file)
                self.assertNotEqual(0,result.returncode)
                self.assertNotIn(b'private-marker',result.stdout)


if __name__ == '__main__': unittest.main()
