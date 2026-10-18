import unittest
from bot import announcement_text
from hacoo_requests import parse_request, find_announcements, prepare_affiliate_post


class Tests(unittest.TestCase):
    def test_request_requires_both_code_and_product_name(self):
        self.assertEqual(parse_request('40763432 | pantalon Adidas'),('40763432','pantalon Adidas'))
        for text in ['40763432','pantalon Adidas','40763432 |', '39123456 | pantalon Adidas']:
            with self.assertRaises(ValueError):parse_request(text)

    def test_search_matches_complete_title_words_and_photos(self):
        posts=[{'source':'a/1','text':'Pantalon Adidas','photos':['a']},
               {'source':'b/1','text':'Chaussures Adidas','photos':['b']},
               {'source':'c/1','text':'Pantalon Adidas','photos':[]},
               {'source':'d/1','text':'Pantalon Adidas homme','photos':['c']}]
        self.assertEqual([p['source'] for p in find_announcements('pantalon adidas',posts)],['a/1','d/1'])
        self.assertEqual(find_announcements('pantalon Nike',posts),[])

    def test_search_handles_accents(self):
        p={'source':'a/1','text':'Écharpe Nike','photos':['a']}
        self.assertEqual(find_announcements('echarpe nike',[p]),[p])

    def test_caption_contains_only_generated_affiliate_link(self):
        original={'source':'a/1','text':'Pantalon Adidas\nhttps://c.onlyaff.app/OTHER\nCode promo: OLD',
                  'photos':['image'],'links':['https://c.onlyaff.app/OTHER']}
        post=prepare_affiliate_post('40763432',original,'https://c.onlyaff.app/ddSN7T')
        text=announcement_text(post)
        self.assertIn('https://c.onlyaff.app/ddSN7T',text)
        self.assertNotIn('OTHER',text)
        self.assertNotIn('OLD',text)
        self.assertIn('Erdezz14',text)
        self.assertEqual(post['photos'],original['photos'])
        self.assertEqual(original['links'],['https://c.onlyaff.app/OTHER'])


if __name__=='__main__':unittest.main()
