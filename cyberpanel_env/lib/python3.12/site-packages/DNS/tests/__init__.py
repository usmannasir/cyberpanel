import unittest
import importlib

def test_suite():
    module_names = [
        '.testPackers',
        '.test_base'
    ]
    suites = []
    for m in module_names:
        module = importlib.import_module(m, 'DNS.tests')
        suites.append(module.test_suite())
    return unittest.TestSuite(suites)
