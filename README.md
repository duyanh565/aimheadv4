# Jerry Mod Chams — Railway deployment

This package serves both UIs and the API from the same Railway service:

- `/` or `/api/chams` — client UI
- `/admin` or `/api/admin` — admin UI
- `/mobileconfig` or `/api/mobileconfig` — NextDNS + mobileconfig builder
- `/api/healthz` — Railway health check

The HTML uses the current Railway origin automatically. If an HTML file is opened directly from disk, it falls back to the Railway URL from the original package: `https://chamv2-production.up.railway.app/api`.

## Deploy

1. Push the contents of this folder to a GitHub repository.
2. Create a Railway service from that repository.
3. Add only `RESET_SECRET` as a Railway variable. Use a random value with at least 32 characters. The server derives separate access-token and refresh-token signing keys internally from it.
4. Deploy, then open the generated Railway URL. The client and admin automatically use that same origin; no API URL is hardcoded in either HTML file.
5. Open `/admin`, choose **Tạo admin lần đầu**, then sign in and create keys.
6. Open `/mobileconfig`, enter a key created in admin, then provide the NextDNS API key, profile ID, domain lists and a `.mobileconfig` template.

For persistent keys and logs, attach a Railway Volume and set `DATA_DIR` to its mount path, such as `/app/data`. Without a volume, SQLite data can be lost when the service is recreated.

## Security behavior

- `RESET_SECRET` has no insecure fallback and the server refuses to start when it is missing. Access-token and refresh-token signing keys are derived internally and are never exposed to the client.
- The target template and search bytes stay server-side.
- The browser receives only short-lived license sessions and color metadata, never the hidden patch template.
- The validated Chams key is stored locally only to support automatic re-login after reload; it is sent only to the configured validation API and is removed when the server rejects it.
- Key duration starts on the first successful key entry, preserving the original lazy-start behavior.
- Key and device IDs keep the `MAKECHAM-XXXXXXXX` format.
- File patching, template construction, validation, and download-token creation happen on the server.
- The mobileconfig builder updates NextDNS through the official API, does not persist the NextDNS API key, and requires the same short-lived license session for generation and download.
- Invalid domains are reported in the result and skipped; valid domains still update NextDNS and generate the mobileconfig.
- The generated mobileconfig is downloaded only after the user presses the download button. On supported iPhone/iPad browsers, the button opens the share sheet so the user can choose “Save to Files”; desktop browsers use a normal file download fallback.
- The mobileconfig builder replaces `PayloadDisplayName`, `PayloadDescription`, NextDNS URLs, `.antiban.<id>` suffixes, and the placeholders `{{CONFIG_NAME}}`, `{{CONFIG_DESCRIPTION}}`, `{{NEXTDNS_ID}}` or `{{PROFILE_ID}}`.
- Removing or hiding the key screen in browser tools does not grant access: `/api/mobileconfig/generate`, `/api/engine-config`, `/api/patch-chams`, and protected downloads validate the license on the server.

The admin reset form requires the private `RESET_SECRET`; it is never embedded in the client.