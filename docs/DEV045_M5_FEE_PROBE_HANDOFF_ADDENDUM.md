# DEV045-M5 Fee Probe Handoff Addendum

Date: 2026-09-03
Status: `PERSONAL_FEE_CAPTURE_PROBE_IMPLEMENTED_CI_PENDING_NO_PNL`

Frozen scientific parent remains:

`DEV045-M5 = cbffd48a9eea77a7ace843f9c830ac96bd39a071`

Current fee-freeze / architecture branch parent before this implementation:

`5734355f99c86f6aef02ee3ede000c53d8824811`

## Purpose

The only remaining pre-M6 scientific blocker is verified personal Binance USD-M Futures fee evidence.

A local-only authenticated probe is now implemented to read the account-specific BTCUSDT commission schedule directly from Binance rather than substitute a public/default fee tier.

Probe:

`tools/dev045_m5_binance_fee_probe.py`

Offline contract tests:

`tests/test_dev045_m5_binance_fee_probe.py`

CI:

`.github/workflows/dev045-m5-fee-probe.yml`

## Authenticated endpoints

Primary fee evidence:

`GET /fapi/v1/commissionRate?symbol=BTCUSDT`

Optional API/eligibility diagnostic:

`POST /fapi/v1/order/test`

The test-order endpoint validates a signed TRADE request but does not create a real order.

## Credential safety

Permanent rules:

- API key and secret are read from hidden local input or environment variables only;
- credentials are never written to the evidence JSON;
- credentials are never committed to Git;
- GitHub Actions contains no Binance secret;
- the probe prints only commission/evidence fields and sanitized exchange errors;
- withdrawal permission is not required and must not be enabled for this research key.

## Scientific safety

The fee capture is evidence collection only.

Even a successful capture leaves:

`primary_fee_schedule_frozen = false`

and:

`m6_authorized = false`

until the captured output is reviewed and explicitly frozen in the M5 personal-fee contract.

No historical data is opened by this probe.
No maker PnL is run.
No M01-M08 rule changes.
No bootstrap/gate changes.
Sep-01+ remains sealed.
Non-BTC remains sealed.

## Next action after CI green

Run the probe locally from the active clone with a dedicated Binance API key that has only the minimum permissions required to read Futures account data. Optionally enable Futures TRADE permission only if running the explicit `/order/test` diagnostic.

Do not paste or commit the API secret.

The resulting sanitized JSON may be shared for review and fee freeze.
