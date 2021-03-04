#TODO: CHECK DIRECTORIES AND FILES NAME

#
# This file is part of LiteHelloWorld.
#

import unittest
import os

def build_config(name):
    errors = 0
    os.system("rm -rf examples/build")
    os.system("cd examples && python3 ../litehelloworld/gen.py {}.yml".format(name))
    errors += not os.path.isfile("examples/build/gateware/litehelloworld_core.v")
    os.system("rm -rf examples/build")
    return errors

class TestExamples(unittest.TestCase):
    def test_wishbone(self):
        errors = build_config("example")
        self.assertEqual(errors, 0)
