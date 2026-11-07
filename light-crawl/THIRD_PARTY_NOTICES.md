# Third-party notices

`light-crawl` is an original MIT-licensed project. It **depends on** and
**integrates with** the projects below. No third-party source code is copied into
this repository; the references summarize public workflows and link to the
upstream documentation.

| Project | License | How light-crawl uses it | What is not included |
|---|---|---|---|
| [Scrapling](https://github.com/D4Vinci/Scrapling) | BSD-3-Clause | Optional Python dependency for fetchers, stealth sessions and spiders | Browser binaries are downloaded separately by `scrapling install` |
| [js-reverse-mcp](https://github.com/zhizhuodemao/js-reverse-mcp) | Apache-2.0 | Optional MCP server, invoked as a separate process | The MCP server is not bundled or modified |
| [REA](https://github.com/morluto/rea) | MIT | Optional CLI/MCP for deep static/runtime analysis | Hopper, IDA, JEB and other commercial engines are not included |
| [reverse-skill](https://github.com/zhaoxuya520/reverse-skill) | MIT (main repository) | Methodology reference for the L2 playbook | Its `CTF-Sandbox-Orchestrator/` GPLv3 submodule and AGPL-licensed external tool are not copied |

## Upstream license texts

When redistributing a bundle that includes any upstream package, keep the
upstream `LICENSE` and `NOTICE` files, and preserve copyright headers. The
canonical texts are in each project's repository:

- Scrapling: <https://github.com/D4Vinci/Scrapling/blob/main/LICENSE>
- js-reverse-mcp: <https://github.com/zhizhuodemao/js-reverse-mcp/blob/main/LICENSE>
- REA: <https://github.com/morluto/rea/blob/main/LICENSE>
- reverse-skill: <https://github.com/zhaoxuya520/reverse-skill/blob/main/LICENSE>

## Commercial tools

REA can integrate with commercial analysis engines. A valid license for those
tools is the user's responsibility. `light-crawl` does not grant, bundle, or
bypass any commercial license.

## Names and trademarks

Scrapling, js-reverse, REA and reverse-skill are the respective projects' names.
This repository does not claim endorsement by their authors.

## No legal advice

This notice is a practical inventory, not legal advice. Re-check the upstream
licenses and your distribution model before publishing a bundled artifact.
