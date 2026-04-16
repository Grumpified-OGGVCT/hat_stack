# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Hat Stack, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Use the [GitHub Security Advisory](https://github.com/Grumpified-OGGVCT/hat_stack/security/advisories/new) to report privately
3. Or email the maintainer directly

Include:
- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Any proposed fix

## Response Time

- Acknowledgment within 48 hours
- Initial assessment within 5 business days
- Security patches released as soon as possible

## Supported Versions

| Version | Supported |
|---------|-----------|
| 3.x     | Yes       |
| < 3.0   | No        |

## Security Features

Hat Stack includes built-in security measures:

- **Local-only mode**: Forces all models to run locally, preventing PII from leaving your machine
- **Sensitive mode**: Automatically detects credentials/API keys in diffs and switches to local models
- **Secret scanning**: GitHub's secret scanning and push protection should be enabled for this repository
- **CodeQL**: Automated code scanning runs on every push and PR

## Responsible Disclosure

We ask that security researchers:
- Allow reasonable time to address the issue before public disclosure
- Avoid accessing or modifying other users' data
- Act in good faith to protect user privacy