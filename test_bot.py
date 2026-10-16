import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import bot

HTML = '''<div class="tgme_widget_message" data-post="source/12">
<div class="tgme_widget_message_text">Chaussures 👟<br>Voir <a href="https://shop.example/p/1">le produit</a></div>
<a class="tgme_widget_message_photo_wrap" style="background-image:url('https://cdn.example/one.jpg')"></a>
<a class="tgme_widget_message_photo_wrap" style="background-image:url('https://cdn.example/two.jpg')"></a>
</div>'''


def post(n, link=None):
    return {'source': f'source/{n}', 'text': f'Annonce produit {n}', 'photos': ['https://cdn4.telesco.pe/photo.jpg'],
            'links': [link or f'https://shop.example/{n}']}


class Tests(unittest.TestCase):
    def test_instance_lock_releases_and_rejects_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bot.lock'
            with bot.instance_lock(path):
                with self.assertRaises(SystemExit):
                    with bot.instance_lock(path):
                        self.fail('Concurrent lock acquired')
            with bot.instance_lock(path):
                pass

    def test_extract_text_hidden_link_and_album(self):
        posts = bot.parse_announcements(HTML)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['source'], 'source/12')
        self.assertEqual(posts[0]['text'], 'Chaussures 👟\nVoir le produit (https://shop.example/p/1)')
        self.assertEqual(len(posts[0]['photos']), 2)
        self.assertEqual(posts[0]['links'], ['https://shop.example/p/1'])
        self.assertEqual(bot.parse_announcements(HTML.replace('</div>', '<video></video></div>', 1)), [])

    @patch('bot.time.sleep')
    def test_batch_persistence_schedule_and_exhaustion(self, sleep):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'history.db'
            db = bot.connect(path)
            bot.ingest(db, [post(n) for n in range(20)])
            sent = []
            class API:
                def publish(self, p): sent.append(p['source'])
            self.assertEqual(bot.run_batch(db, API(), now=10000), 15)
            db.close()
            db = bot.connect(path)
            self.assertEqual(bot.run_batch(db, API(), now=10001), 0)
            self.assertEqual(bot.run_batch(db, API(), now=12700), 5)
            self.assertEqual(len(set(sent)), 20)
            self.assertEqual(bot.run_batch(db, API(), now=15400), 0)
            db.close()

    @patch('bot.time.sleep')
    def test_duplicate_link_and_ambiguous_send(self, sleep):
        db = bot.connect(':memory:')
        bot.ingest(db, [post(1, 'https://same.example'), post(2, 'https://same.example')])
        self.assertEqual(len(bot.choose(db)), 1)
        class Broken:
            def publish(self, p): raise TimeoutError()
        self.assertEqual(bot.run_batch(db, Broken(), now=10000), 0)
        self.assertEqual(bot.choose(db), [])
        self.assertEqual(db.execute("SELECT COUNT(*) FROM posts WHERE state='pending'").fetchone()[0], 1)

    @patch('bot.download_image', return_value=(b'photo-bytes', 'image/jpeg'))
    @patch('bot.time.sleep')
    def test_complete_text_and_photo_calls(self, sleep, download):
        api = bot.Telegram('unused', '@test')
        calls = []
        api.call = lambda method, **kw: calls.append((method, kw))
        p = post(1)
        p['photos'] = ['https://cdn.example/1', 'https://cdn.example/2']
        p['text'] = 'Baskets <édition limitée> 👟\nhttps://shop.example/product\nCode promo : OLD15'
        api.publish(p)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], 'sendMediaGroup')
        media = calls[0][1]['media']
        self.assertEqual(media[0]['media'], 'attach://photo0')
        self.assertIn('<b>Baskets &lt;édition limitée&gt; 👟</b>', media[0]['caption'])
        self.assertIn(bot.PROMO_FOOTER, media[0]['caption'])
        self.assertNotIn('OLD15', media[0]['caption'])
        self.assertNotIn('caption', media[1])
        body, kind = bot.multipart({'chat_id': '@test', 'media': media}, calls[0][1]['_files'])
        self.assertIn(b'photo-bytes', body)
        self.assertIn(b'name="photo0"', body)
        self.assertTrue(kind.startswith('multipart/form-data; boundary='))

    def test_promo_variants_and_duplicate_blocks(self):
        for promo in ['Code promo : prince', '❗️Usa el código "VAMOS"❗️',
                      'Discount Code/Código de descuento= TOP20',
                      '-15% avec le code ANCIEN', 'CODE: OLD15']:
            with self.subTest(promo=promo):
                p = post(1)
                p['text'] = 'Baskets Adidas\nhttps://shop.example/1\n' + promo
                text = bot.announcement_text(p)
                self.assertEqual(text.count('Erdezz14'), 1)
                self.assertNotIn(promo, text)
                self.assertIn('https://shop.example/1', text)
        p['text'] = 'Baskets Adidas\nCode promo: OLD https://shop.example/1'
        self.assertIn('https://shop.example/1', bot.announcement_text(p))
        p['text'] = ('Baskets Adidas\nhttps://shop.example/1\nCode promo: OLD\n') * 2
        self.assertEqual(bot.announcement_text(p).count('Baskets Adidas'), 1)
        self.assertEqual(bot.announcement_text(p).count('https://shop.example/1'), 1)
        p['text'] = bot.announcement_text(p)
        self.assertEqual(bot.announcement_text(p).count('Erdezz14'), 1)

    def test_uniform_template_without_source_hashtags(self):
        p = post(1)
        p['text'] = ('#shopping\nBaskets Adidas #adidas #mode @source\n'
                     'Une longue description propre à la source\n'
                     'Code promo : OLD15\nCheck my bio for more links!')
        p['links'] = ['https://shop.example/p?ref=abc#details']
        expected = ('Baskets Adidas\n\n'
                    'https://shop.example/p?ref=abc#details\n\n' + bot.PROMO_FOOTER)
        self.assertEqual(bot.announcement_text(p), expected)
        self.assertNotIn('#adidas', bot.caption(p))
        self.assertNotIn('@source', bot.caption(p))
        self.assertNotIn('OLD15', bot.caption(p))
        self.assertIn('#details', bot.caption(p))

    def test_quality_and_caption_limits(self):
        p = post(1)
        self.assertTrue(bot.good_announcement(p))
        p['photos'] = []
        self.assertFalse(bot.good_announcement(p))
        p['photos'] = ['https://cdn4.telesco.pe/a']
        p['text'] = '👟' * 600
        self.assertFalse(bot.good_announcement(p))
        p['text'] = 'Code promo: OLD https://shop.example/p'
        self.assertFalse(bot.good_announcement(p))

    @patch('bot.download_image', return_value=(b'image', 'image/jpeg'))
    def test_single_photo_has_full_caption(self, download):
        api = bot.Telegram('unused', '@test')
        calls = []
        api.call = lambda method, **kw: calls.append((method, kw))
        api.publish(post(1))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], 'sendPhoto')
        self.assertIn('Erdezz14', calls[0][1]['caption'])
        self.assertIn('Annonce produit 1', calls[0][1]['caption'])



if __name__ == '__main__':
    unittest.main()
