"""Preparation of a product-code/name request; does not publish or generate links."""
import re
import unicodedata
from bot import product_title
from hacoo_mumu import product_code, affiliate_url


def parse_request(text):
    parts = text.split('|', 1)
    if len(parts) != 2:
        raise ValueError('Envoie le code et le nom : 40763432 | pantalon Adidas')
    code = product_code(parts[0])
    name = parts[1].strip()
    if not 3 <= len(name) <= 160 or not any(c.isalpha() for c in name):
        raise ValueError('Ajoute un nom de produit précis (3 à 160 caractères).')
    return code, name


def words(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return set(re.findall(r'[a-z0-9]+', text))


def find_announcements(name, posts, limit=5):
    query = words(name)
    if not query:
        return []
    candidates = []
    for post in posts:
        title = product_title(post)
        terms = words(title)
        if query.issubset(terms) and 1 <= len(post.get('photos', [])) <= 10:
            candidates.append(post)
    # These are textual candidates, not proof that a photo depicts a product code.
    candidates.sort(key=lambda p: (len(words(product_title(p)) - query), p['source']))
    return candidates[:limit]


def prepare_affiliate_post(code, original, generated):
    """Call only after the product/image association has been checked."""
    code = product_code(code)
    return {**original, 'source': 'hacoo/' + code,
            'original_source': original['source'], 'product_code': code,
            'links': [affiliate_url(generated)]}
