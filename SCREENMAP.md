# SCREENMAP — <Product>

Boxes and arrows. Written during the blockout, checked by `python3 scripts/blockout_check.py`.
Two minutes to write. It is what turns "can someone get lost in this product?" into
a question a computer can answer.

## Format

- `entry:` the screen a user lands on first
- one line per screen: `screen-name -> where you can go from here`
- `roles:` which screens each role is allowed to reach

Every screen id must match a `data-screen="..."` or `id="..."` in the built product.

---

entry: screen-login

screen-login         -> screen-catalog
screen-catalog       -> screen-product, screen-orders, screen-account
screen-product       -> screen-catalog, screen-order-confirm
screen-order-confirm -> screen-orders
screen-orders        -> screen-catalog
screen-account       -> screen-catalog
screen-admin         -> screen-catalog

roles:
  buyer: screen-login, screen-catalog, screen-product, screen-order-confirm, screen-orders, screen-account
  admin: screen-login, screen-catalog, screen-admin, screen-orders

---

## Every screen also needs four states

The checker cannot see these — you check them by clicking. They are the states
that get forgotten when the happy path is built first, and every one of them is a
screen a real user will hit:

| State | The question |
|---|---|
| **empty** | first-ever use, nothing here yet — does it explain what to do? |
| **loading** | is something visibly happening, or does it look frozen? |
| **error** | when it fails, is there a visible message? (not silence, not a raw error) |
| **no permission** | wrong role — does it explain, or just look broken? |
