import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import bot
import hacoo_publish as p
from hacoo_requests import parse_request, prepare_affiliate_post, price_lines


def original():
    return {'source': 'hacoou/123', 'text': 'Nike Pegasus #nike\nA partir de 29,90 €\n'
            'https://c.onlyaff.app/OLD\nCode promo OLD15',
            'photos': ['https://cdn4.telesco.pe/image.jpg'], 'links': ['https://c.onlyaff.app/OLD']}


class Tests(unittest.TestCase):
    def test_comma_request_prices_and_old_link_removed(self):
        self.assertEqual(parse_request('40763432, nike pegasus'), ('40763432', 'nike pegasus'))
        source = original()
        post = prepare_affiliate_post('40763432', source, 'https://c.onlyaff.app/NEW')
        self.assertEqual(post['photos'], source['photos'])
        text = bot.announcement_text(post)
        self.assertEqual(text, 'Nike Pegasus\nA partir de 29,90 €\n\nhttps://c.onlyaff.app/NEW\n\n' + bot.PROMO_FOOTER)
        self.assertNotIn('OLD', text)
        self.assertEqual(price_lines({'text': 'Nike Pegasus\nCode OLD 15%\n40012345'}), [])
        self.assertEqual(source['links'], ['https://c.onlyaff.app/OLD'])

    def test_price_in_title_not_duplicated(self):
        source = original()
        source['text'] = 'Nike Pegasus 29,90 €\nhttps://shop.example/item'
        post = prepare_affiliate_post('40763432', source, 'https://c.onlyaff.app/NEW')
        self.assertEqual(bot.announcement_text(post).count('29,90 €'), 1)

    def test_publish_success_and_uncertain_send_block_retries_after_restart(self):
        for error in [None, TimeoutError()]:
            with self.subTest(error=error), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'history.sqlite3'
                db = p.history(path)
                api = Mock(destination=bot.DESTINATION)
                api.publish.return_value = {'message_id': 12}
                api.publish.side_effect = error
                post = prepare_affiliate_post('40763432', original(), 'https://c.onlyaff.app/NEW')
                if error:
                    with self.assertRaisesRegex(RuntimeError, 'Envoi non confirme'):
                        p.publish_once(db, api, post)
                else:
                    p.publish_once(db, api, post)
                db.close()
                db = p.history(path)
                with self.assertRaises(ValueError):
                    p.publish_once(db, api, post)
                api.publish.assert_called_once()
                state = db.execute('SELECT state FROM affiliate_deliveries').fetchone()[0]
                self.assertEqual(state, 'pending' if error else 'sent')
                db.close()

    @patch('hacoo_publish.webbrowser.open')
    @patch('hacoo_publish.convert')
    @patch('hacoo_publish.search')
    @patch('builtins.input')
    def test_selected_announcement_gets_generated_link_before_publish(self, prompt, search, convert, browser):
        prompt.side_effect = ['40763432, nike pegasus', '1', 'OK', 'PUBLIER']
        search.return_value = [original()]
        convert.return_value = {'affiliate_url': 'https://c.onlyaff.app/NEW'}
        api = Mock(destination=bot.DESTINATION)
        api.publish.return_value = {'message_id': 12}
        db = p.history(':memory:')
        p.run(Mock(), api, db)
        post = api.publish.call_args.args[0]
        self.assertEqual(post['links'], ['https://c.onlyaff.app/NEW'])
        self.assertEqual(post['photos'], original()['photos'])
        self.assertIn('29,90 €', bot.caption(post))
        db.close()

    @patch('hacoo_publish.convert')
    @patch('hacoo_publish.search', return_value=[])
    @patch('builtins.input', return_value='40763432, nike pegasus')
    def test_no_match_never_converts_or_publishes(self, prompt, search, convert):
        db = p.history(':memory:')
        api = Mock(destination=bot.DESTINATION)
        with self.assertRaises(ValueError):
            p.run(Mock(), api, db)
        convert.assert_not_called()
        api.publish.assert_not_called()
        db.close()

    @patch('bot.fetch')
    def test_pagination_uses_oldest_message_even_if_it_has_no_product(self, fetch):
        fetch.side_effect = ['<div class="tgme_widget_message" data-post="hacoou/123"></div>',
                             '<div class="tgme_widget_message" data-post="hacoou/100"></div>', '']
        posts, failed = p.scan_channel('hacoou')
        self.assertEqual(posts, [])
        self.assertFalse(failed)
        self.assertEqual(fetch.call_args_list[1].args[0], 'https://t.me/s/hacoou?before=123')
        self.assertEqual(fetch.call_args_list[2].args[0], 'https://t.me/s/hacoou?before=100')

    @patch('hacoo_publish.webbrowser.open')
    @patch('hacoo_publish.convert')
    @patch('hacoo_publish.search')
    @patch('builtins.input')
    def test_cancel_or_conversion_failure_never_publishes(self, prompt, search, convert, browser):
        search.return_value = [original()]
        for answers, failure in [(['40763432, nike pegasus', ''], False),
                                 (['40763432, nike pegasus', '1', ''], False),
                                 (['40763432, nike pegasus', '1', 'OK', ''], False),
                                 (['40763432, nike pegasus', '1', 'OK'], True)]:
            with self.subTest(answers=answers):
                prompt.side_effect = answers
                convert.side_effect = RuntimeError('Hacoo inaccessible') if failure else None
                convert.return_value = {'affiliate_url': 'https://c.onlyaff.app/NEW'}
                api = Mock(destination=bot.DESTINATION)
                db = p.history(':memory:')
                if failure:
                    with self.assertRaises(RuntimeError):
                        p.run(Mock(), api, db)
                else:
                    p.run(Mock(), api, db)
                api.publish.assert_not_called()
                self.assertEqual(db.execute('SELECT count(*) FROM affiliate_deliveries').fetchone()[0], 0)
                db.close()


if __name__ == '__main__':
    unittest.main()
