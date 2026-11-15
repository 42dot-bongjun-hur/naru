import os
from pathlib import Path

from naru.config import load_config

BASE_DIR = Path(os.environ["NARU_SITE_ROOT"])
OUT_DIR = Path(os.environ["NARU_OUTPUT_DIR"])
DATA_DIR = BASE_DIR / "content" / "data"
POSTS_DIR = BASE_DIR / "content" / "posts"
TPL_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

_settings = load_config(BASE_DIR / "naru.yml")
SITE_ORIGIN = _settings["site_origin"]
SITE_NAME = _settings["site_name"]
SITE_SLOGAN_EN = _settings["site_slogan_en"]
SITE_SLOGAN_KO = _settings["site_slogan_ko"]
SITE_TAGLINE = _settings["site_tagline"]
SITE_DESCRIPTION = _settings["site_description"]
CATEGORY_LABELS = _settings["category_labels"]
CATEGORY_REDIRECTS = _settings["category_redirects"]
BASE_URL = _settings["base_url"]
POSTS_URL_PREFIX = _settings["posts_url_prefix"]
CATEGORY_URL_PREFIX = _settings["category_url_prefix"]
TAG_URL_PREFIX = _settings["tag_url_prefix"]
POSTS_PER_PAGE = _settings["posts_per_page"]
RSS_ITEM_LIMIT = _settings["rss_item_limit"]
RSS_TITLE = _settings["rss_title"]
RSS_DESCRIPTION = _settings["rss_description"]
HOME_CATEGORY_GROUPS = _settings["home_category_groups"]
HOME_CATEGORY_ORDER = _settings["home_category_order"]
HOME_POSTS_PER_CATEGORY = _settings["home_posts_per_category"]
HOME_RECENT_POSTS = _settings["home_recent_posts"]
HOME_MAX_ADS = _settings["home_max_ads"]
INLINE_AD_CHARS = _settings["inline_ad_chars"]
INLINE_AD_MAX = _settings["inline_ad_max"]
ADSENSE_PUB_ID = _settings["adsense_pub_id"]
AD_SLOT_TOP = _settings["ad_slot_top"]
AD_SLOT_MID = _settings["ad_slot_mid"]
AD_SLOT_SIDE = _settings["ad_slot_side"]
AUTHOR_NAME = _settings["author_name"]
AUTHOR_BIO = _settings["author_bio"]
AUTHOR_NOTES = _settings["author_notes"]
AUTHOR_NOTE_DEFAULT = _settings["author_note_default"]
