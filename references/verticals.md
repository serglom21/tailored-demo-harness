# Starter journeys by vertical

Use these only when the context is thin. **Customer context always wins:** replace generic attributes with the customer's own words as soon as you have them.

| Vertical | Journeys | Attributes worth slicing by | Failure modes that land well |
|---|---|---|---|
| E-commerce / retail | browse → search → add-to-cart → checkout | `payment_provider`, `cart_size_bucket`, `region`, `device_class` | payment gateway timeout, inventory check 5xx, slow search on large catalogs |
| Fintech / payments | onboarding/KYC, transfer, card authorization | `kyc_vendor`, `transfer_rail` (ach/wire/rtp), `risk_tier`, `country` | KYC vendor latency, ledger lock contention, idempotency conflict |
| Media / streaming | sign-in, browse, playback start | `cdn`, `bitrate_tier`, `device_platform`, `content_type` | slow time-to-first-frame, DRM license failure, CDN failover |
| SaaS / B2B | sign-in/SSO, core workflow (create/save/export), search | `plan_tier`, `workspace_size_bucket`, `sso_provider`, `feature_flag` | export job timeout, SSO callback error, N+1 on large workspaces |
| Travel / marketplace | search, quote/pricing, booking | `supplier`, `market`, `party_size_bucket` | supplier API timeout, price changed at booking, stale cache |
| Gaming / mobile | app start, login, matchmaking/store purchase | `os_version_bucket`, `device_tier`, `store` (apple/google) | cold start regression, purchase verification failure, ANR on low-end devices |
| Healthcare | patient login, scheduling, records view | `clinic_region`, `integration` (ehr vendor), `appointment_type` | EHR integration timeout, slow records render (no PHI ever) |
| AI products | prompt → model call → tool calls → response | `model`, `provider`, `tool_name`, `prompt_tokens_bucket` | provider rate limit, tool call error, slow time-to-first-token |

## Turning context into journeys

1. Start from the customer's **compelling event**. The journey that caused it is journey #1.
2. Add the journey their **exec** cares about (revenue or conversion), if it's a different one.
3. Add at most one "wow" journey, such as frontend→backend→third-party tracing or a mobile cold start, but only if it maps to their stack.
4. Stop at 4. A tight demo beats a wide one.
