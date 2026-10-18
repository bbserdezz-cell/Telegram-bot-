import unittest
import subprocess
from unittest.mock import patch
import hacoo_mumu as h


def screen(text=''):
    return f'''<hierarchy><node text="Link Customize" bounds="[0,0][100,30]"/>
    <node class="android.widget.EditText" text="{text}" bounds="[10,40][200,100]"/>
    <node text="Create Link" bounds="[10,110][200,160]"/></hierarchy>'''

RESULT = '''<hierarchy><node text="Promote Link"/><node text="https://c.onlyaff.app/ddSN7T"/></hierarchy>'''


class Tests(unittest.TestCase):
    @patch('hacoo_mumu.subprocess.run')
    def test_dump_nonzero_with_fresh_valid_xml_is_accepted(self, run):
        run.side_effect = [subprocess.CompletedProcess([], 1, b'UI hierarchy dumped'),
                           subprocess.CompletedProcess([], 0, screen().encode()),
                           subprocess.CompletedProcess([], 0, b'')]
        self.assertEqual(h.Adb('adb.exe', 'device').screen(), screen())
        dump, read, cleanup = run.call_args_list
        self.assertFalse(dump.kwargs['check'])
        self.assertEqual(dump.args[0][-1], read.args[0][-1])
        self.assertEqual(read.args[0][-1], cleanup.args[0][-1])
        self.assertNotEqual(read.args[0][-1], '/sdcard/hacoo-automation.xml')

    @patch('hacoo_mumu.subprocess.run')
    def test_dump_success_without_valid_xml_is_rejected(self, run):
        for invalid in [b'', b'<hierarchy/>', b'<unrelated><node/></unrelated>', b'<hierarchy>']:
            with self.subTest(xml=invalid):
                run.side_effect = [subprocess.CompletedProcess([], 0, b'success'),
                                   subprocess.CompletedProcess([], 0, invalid),
                                   subprocess.CompletedProcess([], 0, b'')]
                with self.assertRaises(h.AutomationError):
                    h.Adb('adb.exe', 'device').screen()

    def test_codes_and_url(self):
        self.assertEqual(h.product_url('40763432'), 'https://hacoo.pl/detail/40763432')
        self.assertEqual(h.product_code('4012345'), '4012345')
        for code in ['39123456', '40xxxxxx', '407634321', '4076;432', '٤٠٧٦٣٤٣٢']:
            with self.assertRaises(ValueError): h.product_code(code)

    def test_result_requires_dialog_and_unique_valid_link(self):
        self.assertEqual(h.generated_link(RESULT), 'https://c.onlyaff.app/ddSN7T')
        for bad in [RESULT.replace('Promote Link','Other'), RESULT.replace('</hierarchy>', '<node text="https://c.onlyaff.app/other"/></hierarchy>')]:
            with self.assertRaises(h.AutomationError): h.generated_link(bad)
        for bad in ['http://c.onlyaff.app/x', 'https://c.onlyaff.app.evil.test/x', 'https://user@c.onlyaff.app/x']:
            with self.assertRaises(h.AutomationError): h.affiliate_url(bad)

    @patch('hacoo_mumu.time.sleep')
    def test_conversion_checks_input_then_creates(self, sleep):
        class Fake:
            def __init__(self): self.screens=iter([screen('old'),screen(h.product_url('40763432')),RESULT]);self.taps=[];self.commands=[]
            def screen(self): return next(self.screens)
            def tap(self,node):self.taps.append(h.label(node))
            def run(self,*args):self.commands.append(args)
        adb=Fake()
        self.assertEqual(h.convert(adb,'40763432')['affiliate_url'],'https://c.onlyaff.app/ddSN7T')
        self.assertEqual(adb.taps[-1],'Create Link')
        self.assertIn(('shell','input','text','https://hacoo.pl/detail/40763432'),adb.commands)

    def test_wrong_screen_or_unverified_input_stops(self):
        class Fake:
            def __init__(self, screens):self.screens=iter(screens);self.taps=[]
            def screen(self):return next(self.screens)
            def tap(self,node):self.taps.append(h.label(node))
            def run(self,*args):pass
        for screens in [[RESULT], [screen(),screen('wrong')]]:
            adb=Fake(screens)
            with self.assertRaises(h.AutomationError):h.convert(adb,'40763432')
            self.assertNotIn('Create Link',adb.taps)


if __name__ == '__main__': unittest.main()
