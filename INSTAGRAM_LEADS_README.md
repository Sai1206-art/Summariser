# Instagram Comment Leads

Turns the comment section of an Instagram reel or post into a ranked lead list.

Page: `/instagram_leads` · API: `POST /api/instagram_leads`

## What it does

1. Collects the comments of a reel/post (two sources, see below).
2. Scores every comment for buying intent — price/brochure/site-visit/EMI questions,
   "DM me" / "interested" / WhatsApp requests, shared phone numbers and emails.
3. Grades each commenter **hot / warm / cold**, shows a summary, and exports the
   ranked list as CSV (username, profile URL, comment, signals, phones, emails).

## Two ways to get comments

### 1. Your own posts/reels — official Instagram Graph API

Paste the post/reel URL. Works only for media on the Instagram **Business/Creator
account connected to your Meta app** (Instagram's API does not expose other
accounts' comments, and the page will say so if the post isn't yours).

Environment variables:

```
INSTAGRAM_ACCESS_TOKEN=...            # Meta Graph API token (required)
INSTAGRAM_BUSINESS_ACCOUNT_ID=...    # optional; auto-discovered via /me/accounts if omitted
DEBUG_INSTAGRAM=1                     # optional; server-side error logging
```

Token requirements: a long-lived token for a Meta app with `instagram_basic`,
`instagram_manage_comments`, and `pages_show_list` permissions, generated for the
Facebook Page linked to the IG account.

### 2. Anyone's public post — import an export

Use the Import tab to paste or upload a **PhantomBuster "Instagram Post Commenters"
export** (JSON or CSV), or any CSV/JSON of comments. Column names are matched
flexibly (`comment`/`commentText`/`text`/`message` for the text,
`username`/`handle`/`author` for the commenter, etc.).

The existing PhantomBuster webhook (`/api/webhook/phantombuster`) can be pointed at
this same analyzer later if you want fully automated runs.

## Notes

- Scoring is keyword-based and tuned for real-estate intent (price, brochure,
  site visit, payment plan, EMI, location) plus generic signals (questions, DMs,
  shared contact info). Adjust `INTENT_KEYWORDS` in
  `src/app/api/instagram_leads/route.ts` to retune.
- Scraping Instagram directly without their API violates Meta's Terms of Service;
  this feature therefore only uses the official API for your own media and accepts
  data exports for everything else.
