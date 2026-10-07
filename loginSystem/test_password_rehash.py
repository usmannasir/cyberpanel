#!/usr/bin/env python
import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from plogical import hashPassword as hp

class PasswordRehashTests(unittest.TestCase):
    def test_needs_rehash_legacy(self):
        self.assertTrue(hp.needs_password_rehash('sha1$abc'))

    def test_bcrypt_no_rehash(self):
        self.assertFalse(hp.needs_password_rehash('$2b$12$abcdefghijklmnopqrstuv'))

if __name__ == '__main__':
    unittest.main()
