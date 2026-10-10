# scanner-tv-relay

Vercel Function `POST /api/tv` that receives TradingView alert webhooks and forwards them
to the "קליטת התראות TradingView" routine webhook with the required Authorization header.

## Env vars (Vercel project settings → Environment Variables, Production)
| Name | Required | Type | Meaning |
|---|---|---|---|
| `TV_SHARED_SECRET` | yes (already set) | sensitive | Must equal the `"secret"` field in the TradingView alert JSON. Copy on the box: `/workspace/tradingview/.relay_secret` (chmod 600). |
| `ROUTINE_WEBHOOK_URL` | to forward | sensitive | Full https URL of the routine webhook. |
| `ROUTINE_AUTH_HEADER` | to forward | sensitive | Full value of the Authorization header, e.g. `Bearer <routine key>`. |
| `TV_IP_CHECK` | optional | plain | `1` = only accept TradingView's IPs (52.89.214.238, 34.212.75.30, 54.218.53.128, 52.32.178.7). |

After changing env vars, redeploy production (env vars apply to new deployments only).

## Responses
- 200 `{ok:true, forwarded:"queued"}`: accepted, forwarding in background (waitUntil, 10 s timeout)
- 200 `{ok:true, forwarded:false, note:"forward not configured"}`: accepted, URL/header not set yet
- 400 malformed JSON / not an object · 401 wrong or missing secret · 403 IP not allowed (TV_IP_CHECK=1)
- 405 non-POST · 413 body > 16 KB · 500 TV_SHARED_SECRET missing

The `secret` field is stripped before forwarding; `relay_received_at` (ISO UTC) is added.
Logs never contain the secret, the auth header, the routine URL or the body.

## TradingView alert message template
```json
{"secret":"<TV_SHARED_SECRET>","ticker":"{{ticker}}","exchange":"{{exchange}}","interval":"{{interval}}","time":"{{time}}","timenow":"{{timenow}}","close":{{close}}}
```
Webhook URL: `https://scanner-tv-relay.vercel.app/api/tv` (port 443 only).

## Deployment (2026-10-08)
- Vercel project: `scanner-tv-relay` (id prj_3xDP3piZsQM6iSRWf6vyl9FkFv29), standalone project
- Production endpoint: https://scanner-tv-relay.vercel.app/api/tv (region iad1, Node 22)
- First deployment: dpl_47dumowQzawNdydqU7jVXBc39D9t
- Vercel Authentication (SSO protection): disabled for this project only (was on by default)
- Env set: TV_SHARED_SECRET (sensitive), TV_IP_CHECK=0. Not yet set: ROUTINE_WEBHOOK_URL, ROUTINE_AUTH_HEADER
