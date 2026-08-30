# Verified multi-turn demo transcript

Generated locally on 30 August 2026 with:

```bash
python3 demo.py --top-k 3
```

The demo uses the authorized 50,000-product catalog, no evaluator ground truth, no scenario label at runtime, no model, and no network call.

## Browsing session

**Customer:** I'm looking for wallets, but I'm still exploring.

**Agent:** Here are the closest matches. What specific requirement matters most?

**Structured question:** `other`

1. US Armed Forces Collection Mens Genuine Leather Wallets, `B01AKEUFY6`
2. Tommy Hilfiger Womens Core Wallets Continental Checkbook Wallet, `B06Y5F3JD9`
3. Roxy Women's Territory Wallets, `B010LF5I0A`

**Customer:** For that, what matters is: leather; color: black.

**Agent:** Here are the closest matches. What specific requirement matters most?

**Structured question:** `other`

1. NOVICA Handmade Men's Leather Wallet Black, `B016QUDKCW`
2. Polo Ralph Lauren Black Leather Men Bifold Wallet, `B00793M0Z4`
3. Coach Black Patent Leather Medium Corner Zip Wallet, `B07GXB6MPF`

## What this proves

The Agent retains the requested category across turns, asks a legal structured clarification, incorporates later material and color evidence, and returns ordered catalog-valid product IDs. It does not prove that any recommendation is the organizer's hidden target, that all natural-language overrides are fully understood, or that private-set performance matches the public result.
