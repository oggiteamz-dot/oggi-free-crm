# <Product>

Built and maintained with the OGGI Build system.

## The three commands

```
just census        is my computer the same as what's live?
just check         green or red, under a minute
just verify-live   does it work for a real customer, on a second device?
```

If a word in any output is unfamiliar, it's in `GLOSSARY.md`.
If something is red and you're not sure what to do, `HOW-TO-CHECK-MY-APP.md`.

## First-run checklist

- [ ] `oggi-build.config.json` — live URL, source folders, and the save list
- [ ] `scripts/deploy.sh` — the one front-end line for this product
- [ ] `verify.journeys.json` — at least payment, sign-in, and the main action
- [ ] `just adopt` — only if this product already existed before the toolkit
