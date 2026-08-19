# Third-party assets

## qrcode.min.js

- [qrcodejs](https://github.com/davidshimjs/qrcodejs) v1.0.0, MIT licensed
- Source: `https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js`
- SHA-256: `c541ef06327885a8415bca8df6071e14189b4855336def4f36db54bde8484f36`

Bundled rather than loaded from a CDN: a Home Assistant instance often has no
outbound internet access, and a login page should not run third-party script.

To update it, re-download the file and update the hash above.
