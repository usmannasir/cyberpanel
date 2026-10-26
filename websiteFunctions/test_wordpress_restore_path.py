import tempfile
from pathlib import Path
import unittest
from websiteFunctions.wordpressRestore import validate_restore_path

class RestorePathTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'public_html';self.root.mkdir()
    def test_empty_path_selects_document_root(self):
        self.assertEqual(('', '1'),validate_restore_path(str(self.root),''))
    def test_nested_relative_path_is_preserved(self):
        self.assertEqual(('blog/news-1', '0'),validate_restore_path(str(self.root),'blog/news-1/'))
    def test_traversal_absolute_shell_and_malformed_inputs_refuse(self):
        for value in ('../other','blog/../../other','/tmp/other','blog//other','./blog','blog/./other','foo..bar','blog;id','blog x','blog\nother','blog\\other',None,1,True,'a'*201):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):validate_restore_path(str(self.root),value)
    def test_symlink_escape_refuses(self):
        outside=Path(self.tmp.name)/'outside';outside.mkdir();(self.root/'escape').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):validate_restore_path(str(self.root),'escape/child')
    def test_symbolic_document_root_refuses(self):
        link=Path(self.tmp.name)/'linked_root';link.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):validate_restore_path(str(link),'')
    def test_contained_symlink_resolves_inside_authorized_root(self):
        (self.root/'actual').mkdir();(self.root/'inside').symlink_to(self.root/'actual',target_is_directory=True)
        self.assertEqual(('inside/child','0'),validate_restore_path(str(self.root),'inside/child'))
