import io
import textwrap
from datetime import datetime
from json import load
import yake
import FinNews as fn
import re
import tweepy
from PIL import Image, ImageDraw, ImageFont

# Objects
kw_extractor = yake.KeywordExtractor(n=1)

news = fn.CNBC(topics=['finance'])

template = Image.open("./template.jpg")

config = load(open("./config.json"))

auth = tweepy.OAuth1UserHandler(
    consumer_key=config['consumer']['key'],
    consumer_secret=config['consumer']['secret'],
    access_token=config['access']['key'],
    access_token_secret=config['access']['secret']
)
twitter = tweepy.API(auth)

# Globals
size = template.width
font = 400
hashtag_re = re.compile("[^A-Za-z0-9]")


# Last date
last_tweet = datetime.fromtimestamp(float(open("./latest.txt", "r").read()))
new_last_tweet = 0

for idx, article in enumerate(news.get_news()[::-1]):
    try:
        # skip if already known
        curr_date = datetime(
            year=article.published_parsed.tm_year,
            month=article.published_parsed.tm_mon,
            day=article.published_parsed.tm_mday,
            hour=article.published_parsed.tm_hour,
            minute=article.published_parsed.tm_min,
            second=article.published_parsed.tm_sec
        )
        if curr_date < last_tweet:
            continue
        new_last_tweet = max(curr_date.timestamp(), new_last_tweet)

        # create image
        img = template.copy()
        fnt = ImageFont.truetype("./font.ttf", font)
        canvas = ImageDraw.Draw(img)

        # draw text
        lines = "\n".join(textwrap.wrap(article.title, width=font * 256 // size))
        canvas.text((size / 2, size / 2), lines, font=fnt, anchor="mm", align="center")

        # figure out hashtags
        keywords = kw_extractor.extract_keywords(f"{article.title} {article.summary}")
        keywords = ["#"+hashtag_re.sub("", key[0]) for key in keywords if key[1] < 0.12]

        # save and upload image
        img.thumbnail((512, 512))
        f = io.BytesIO()
        img.save(fp=f, format="png")
        f.seek(0)
        media = twitter.media_upload(
            f"article_{idx}.png",
            file=f,
            media_category="TweetImage"
        )

        # figure out tweet content
        content = f"{article.summary}\nSource: {article.link}"
        tags = config['tags'] + keywords
        while len(tags) > 0 and len(content) + 1 + len(tags[0]) < 280:
            content += f" {tags.pop(0)}"
        content = content[:280]

        # tweet
        twitter.update_status(content, media_ids=[media.media_id])
        print(content)
    except Exception as ex:
        print(f"\t{ex}")

if new_last_tweet > 0:
    with open("./latest.txt", "w+") as fp:
        fp.write(f"{new_last_tweet}")
