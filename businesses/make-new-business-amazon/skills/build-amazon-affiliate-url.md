# Build Amazon affiliate URL

- Scope: business (make-new-business-amazon)
- Risk: medium

Construct Associate links using `AMAZON_ASSOCIATE_TAG` from environment. Never store the
tag in repo files.

## Steps

1. Read tag via `app.affiliate.affiliate_tag()` (env default `yourtag-20`).
2. Build `https://www.amazon.com/dp/{asin}?tag={tag}`.
3. Add #ad disclosure to every TikTok caption using the link.

## Verify

```bash
AMAZON_ASSOCIATE_TAG=demo-20 python -c "from app.affiliate import build_affiliate_url; print(build_affiliate_url('B0TEST'))"
```
