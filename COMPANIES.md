# Tracked Companies

Companies currently tracked by the job alert bot, grouped by ATS connector. Source of truth is [companies.json](companies.json).

## Google (custom connector)
- Google

## Apple (custom connector)
- Apple

## Amazon (custom connector)
- Amazon

## Goldman Sachs (custom connector)
- Goldman Sachs

## Microsoft (custom connector)
- Microsoft

## TikTok (custom connector)
- TikTok

## Workday
- Salesforce
- Nike
- Target
- Comcast
- Visa
- T-Mobile
- Adobe
- Mastercard
- PayPal

## Greenhouse
- Stripe
- Robinhood
- Coinbase
- Airbnb
- Instacart
- Reddit
- Pinterest
- Discord
- Duolingo
- Affirm
- Brex
- Chime
- Lyft
- Figma
- Webflow
- Asana
- Vercel
- Gusto
- Doximity
- Databricks
- GitLab
- Dropbox
- Squarespace
- Peloton
- Roblox
- SoundCloud
- Anthropic
- Datadog
- Fivetran
- Scale AI
- Cloudflare
- MongoDB
- Elastic
- CockroachDB
- New Relic
- Sumo Logic
- PagerDuty
- LaunchDarkly
- Samsara
- Postman
- Twilio
- Okta
- Zscaler
- Smartsheet
- Mixpanel
- Klaviyo
- Braze
- Intercom
- Contentful
- Airtable
- Calendly
- Block
- SoFi
- Betterment
- Upstart
- Carta
- Marqeta
- Gemini
- Checkr
- Justworks
- Oscar Health
- Toast
- Faire
- Flexport

## Ashby
- Notion
- Linear
- Ramp
- Vanta
- OpenAI
- Watershed
- Amplitude
- Snowflake
- Airbyte
- Clay
- Cohere
- Perplexity
- Cursor
- Replit
- Sierra
- Harvey
- Baseten
- Modal
- Supabase
- Render
- Temporal
- Drata
- Zip
- ElevenLabs

## Lever
- Spotify
- Palantir
- Gopuff

---

**Total: 106 companies**

---

**Investigated and deliberately not added:**
- **Tesla** -- careers.tesla.com sits behind Akamai Bot Manager (a live bot-detection challenge cookie, `_abck`, was confirmed on the page). Circumventing that would mean bypassing real bot-detection, which this project won't do. No connector was built.
- **Meta** -- metacareers.com job search only goes through Facebook's internal CSRF-token-gated "Comet" GraphQL infrastructure, not a stable public API. Same instability class as the risk already flagged in `connectors/google.py`'s own comment. No connector was built.
