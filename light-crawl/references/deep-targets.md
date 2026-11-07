# Deep targets with REA (L4)

## 1. When to use REA

Use `L4_APP` only when the browser surface is insufficient:

- the service is a desktop Electron app;
- the data is only exposed to an APK/IPA;
- the protocol lives in a native binary or firmware;
- you have a HAR/SAZ/pcap and need to reconstruct the request contract;
- the website calls an app-only signed endpoint;
- you need a static JavaScript/ASAR inventory with evidence.

Do not use REA for a normal HTML page. It is heavier than Scrapling and js-reverse
and adds no value when an HTTP endpoint already works.

## 2. CLI first

Static JavaScript/ASAR work does not require the REA MCP. Use the project-local
launcher so nothing is installed into the global npm prefix:

```powershell
& "D:\Light-Science\light-crawl\scripts\rea.ps1" analyze-javascript-application "D:/path/to/app" --format json
```

The wrapper runs `npx -y rea-agents@latest`; the first run populates npm's cache
and later runs reuse it. There is no global REA install to clean up.

Write the result to `artifacts/rea-js-app.json` and add an evidence entry. The
result contains modules, imports, source maps, routes, IPC boundaries and
limitations.

## 3. MCP on demand

Register the MCP only when interactive tools are needed:

```bash
npx rea-agents setup --client codex
```

This writes configuration and installs matching instructions. Review the proposed
paths and backups first. Restart the agent after setup.

Useful target routes:

| Target | Tool |
|---|---|
| Extracted JS/Electron tree | `analyze_javascript_application` |
| ASAR/APK/IPA/MSIX archive | `open_binary`, `inspect_artifact` |
| Android package | `inspect_android_package` |
| Managed PE/.NET | `inspect_managed_artifact` |
| Browser page | `list_browser_targets`, `capture_browser_scenario` |
| Electron runtime | `list_electron_targets`, `inspect_electron_fuses` |
| HAR/SAZ | `inspect_web_network_capture` |
| Native binary | `open_binary` + focused analysis |
| Firmware | `inspect_firmware_regions`, `extract_firmware` |

## 4. HAR/SAZ handoff

If js-reverse or Scrapling captured a session, export a HAR and inspect it with
REA:

```text
inspect_web_network_capture(path="har/session.har", format="har")
```

Look for:

- the request that returns the item list;
- required headers and cookies;
- request body and query parameters;
- redirects and token refresh;
- WebSocket upgrade and message frames.

Then write the contract to `fixtures/request.json` and hand it to `L0_API`.

## 5. Evidence model

REA distinguishes observations, inferences and unknowns. Keep that discipline in
`evidence.jsonl`:

```json
{
  "phase": "UNDERSTOOD",
  "source": "rea",
  "action": "analyze_javascript_application",
  "observation": "module `api/client.js` builds `/v2/items` and signs with `x-sign`",
  "inference": "the signature input is method + path + body hash",
  "confidence": "medium",
  "artifact": "artifacts/rea-js-app.json",
  "metadata": {"evidence_ids": ["..."]}
}
```

Do not paste a whole decompiled file into the chat. Save it, cite the file, and
quote the smallest relevant range.

## 6. Requirements

- Node.js 22.x (>=22.23.4), 24.x, or 26.12.1+ for current REA releases.
- Hopper/Ghidra/IDA only for deep native analysis.
- JADX/JDK only for Android decompilation.
- TShark/capinfos only for packet captures.
- Commercial tools require a valid license; `light-crawl` does not bundle them.

## 7. Stop conditions

- The app requires a device attestation or hardware key you do not control.
- The only path is bypassing a license or DRM.
- The target is not owned or authorized.
- The analysis requires a commercial tool the user does not have.
- The evidence is too weak to support the claimed endpoint or algorithm.

## 8. Output contract

Return to the acquisition lane with:

1. endpoint(s), method(s), headers, cookies;
2. request/response fixtures (redacted);
3. signing/encryption inputs and a reproduction note;
4. pagination/cursor rules;
5. rate-limit/auth constraints;
6. unresolved unknowns.

If you cannot produce a replayable request, the case is not ready for a spider.
