# QR Login for Home Assistant

Sign in to Home Assistant without retyping your password and OTP every time —
from an incognito window, a shared computer, or a new browser — by approving
the request from a device that is already signed in.

It is the same idea as WhatsApp Web, and follows the shape of the OAuth Device
Authorization Grant (RFC 8628): the browser that wants in is anonymous, and a
second, already-authenticated device decides whether to let it through.

Everything is configured from the UI. No YAML.

## How it works

You open `/qr_login/start` on the device you want to sign in on and pick one of
two channels:

**QR code** — the page shows a QR code. Scan it with any device. The approval
page it opens works out how to authenticate you: a browser that already has a
Home Assistant session shows the request straight away, the Companion App
authenticates through its native bridge, and a browser with no session is
offered the app or a normal login instead of a dead end.

**Push notification** — you type the username you are requesting access for. If
it matches a configured mapping, an actionable notification goes to the
approving device with **Approve** / **Reject** buttons. Nothing else to open.

Either way the approver sees the requesting IP and user agent, and which
account the token will be issued for, before confirming. The waiting browser
then picks up the result and is signed in.

## Installation

Requires Home Assistant 2024.6 or newer.

### HACS

Add `https://github.com/luivit/qr_login` as a custom repository of type
*Integration*, install **QR Login**, then restart Home Assistant.

### Manually

1. Copy `custom_components/qr_login/` into your `config/custom_components/`.
2. Restart Home Assistant.

Either way, finish with **Settings → Devices & Services → Add integration →
QR Login**.

## Configuration

The options flow covers enabled channels, reCAPTCHA v3, rate limiting, the
notification cooldown and the session timeout.

**User mappings** are what make the push channel useful. Each entry maps a
username someone can type to the Home Assistant account the token is issued
for, plus the device that receives the approval request. The two need not be
the same person — an administrator can approve access for a dedicated
non-admin service account.

Without a mapping the token is always issued for whoever approves: a username
typed by an anonymous requester is only a lookup key, never a target.

## Admin panel

A **QR Login** entry appears in the sidebar for administrators, listing the
requests currently in flight with their IP, user agent, target account and
time left, and letting you cancel any of them. Below it, a short history of
recently resolved requests and how they ended.

## Security

- Session ids are `secrets.token_urlsafe(24)`, single use, and expire after
  120 seconds by default.
- Issuing a token for an account other than the approver's own requires
  administrator rights.
- The response to a login request is identical whether or not the username
  exists, so it cannot be used to enumerate accounts.
- Per-IP and global rate limiting on the public endpoint, plus an optional
  server-side reCAPTCHA v3 check.
- `switch.qr_login_enabled` disables everything instantly, including requests
  already in flight.
- The pages load no third-party script and no remote fonts, so they work on an
  instance with no outbound internet access.
- Issued tokens are ordinary Home Assistant refresh tokens: they show up under
  active sessions and can be revoked from the native UI.

Behind a reverse proxy, set `use_x_forwarded_for` and `trusted_proxies` in
`http:` so per-IP rate limiting sees the real client address.

## Languages

English is the base language, with Italian included. Config flow strings live
in `strings.json` and `translations/`, page strings in
`www/static/i18n.js`, and the push notification wording in
`notify_channel.py`.

## License

[MIT](LICENSE). Bundles [qrcodejs](https://github.com/davidshimjs/qrcodejs)
v1.0.0 (MIT); see
[`custom_components/qr_login/www/static/README.md`](custom_components/qr_login/www/static/README.md).
