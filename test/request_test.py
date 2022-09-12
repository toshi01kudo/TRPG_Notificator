import unittest, sys
sys.path.append('..')
# from .. import TRPG_notificator
import TRPG_notificator

class TestRequest(unittest.TestCase):
    def test_web_access(self):
        mono_list = TRPG_notificator.get_info_from_monodraco()
        dayd_list = TRPG_notificator.get_info_from_daydream()

        self.assertGreater(len(mono_list), 0)
        self.assertGreater(len(dayd_list), 0)

if __name__ == "__main__":
    unittest.main()
