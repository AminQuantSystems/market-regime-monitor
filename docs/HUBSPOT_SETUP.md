# HubSpot setup for demonstration leads

The running application uses a HubSpot Service Key. It does not create properties and it does not use a legacy private app.

## Service Key

Official management paths, as documented for Service Keys:

- Development → Keys → Service keys → Create service key
- Settings → Integrations → Service Keys, where that menu is shown

Name the key `MEEM Market Regime Demo`.

Select only these scopes:

- `crm.objects.contacts.read`
- `crm.objects.contacts.write`
- `crm.objects.companies.read`
- `crm.objects.companies.write`

Those four scopes cover contact and company reads, writes, search, and the default contact-to-company association used here. HubSpot’s September 2026 write-validation note about the separate “Edit Associations” permission applies to user-level OAuth. It does not apply to a portal Service Key. Do not add that scope unless a live association call returns a scope error naming it.

Do not add deals, tickets, marketing email, CMS, payments, commerce, custom objects, files, workflows, or schema write.

The property check script can return a refusal to read property definitions. That check, and only that check, needs `crm.schemas.contacts.read`. The application does not. Do not add `crm.schemas.contacts.write`.

Store the key in the local environment as `HUBSPOT_SERVICE_KEY`. Do not put it in source, GitHub, the image, or a report.

## Properties

Create these on the contact object before enabling the public form. Settings → Properties → Contact properties → Create property. If the account groups settings under Data Management, open Properties from there.

Use the existing Contact information group. Set the internal name exactly. For the dropdown, set each option’s label and internal value to the same word.

| Label | Internal name | Type | Values |
| --- | --- | --- | --- |
| MEEM demo status | `meem_demo_status` | Dropdown select | `REQUESTED`, `EMAIL_VERIFICATION_SENT`, `EMAIL_FAILED`, `ACCESS_GRANTED`, `EXPIRED`, `REVOKED` |
| MEEM demo requested at | `meem_demo_requested_at` | Date and time | |
| MEEM demo verified at | `meem_demo_verified_at` | Date and time | |
| MEEM demo access expires at | `meem_demo_access_expires_at` | Date and time | |
| MEEM demo request id | `meem_demo_request_id` | Single-line text | |
| MEEM demo verification jti | `meem_demo_verification_jti` | Single-line text | |
| MEEM demo access jti | `meem_demo_access_jti` | Single-line text | |
| MEEM demo interest | `meem_demo_interest` | Multi-line text | |

Do not create `meem_demo_product`, `meem_demo_source`, or `meem_demo_email_type`. Name, email, job title, company name, and company domain use HubSpot’s standard properties.

The free account’s published allowance is 10 custom properties in total. These eight are the ceiling for this integration. Leave the remaining capacity unused.

Check them, without creating anything, with:

```bash
python scripts/verify_hubspot_setup.py
```

The script reads `HUBSPOT_SERVICE_KEY` from the environment and does not print it.
