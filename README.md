# 🧠 CORTEX OSINT Starter Pack

> **Free, open-source OSINT investigation domain pack for the [CORTEX Intelligence Platform](https://fatcrapinmybutt.github.io/cortex-site/).**

[![Download CORTEX](https://img.shields.io/badge/Download-CORTEX%20Pro-00d4ff?style=for-the-badge)](https://andrewpioneer6.gumroad.com/l/cjamvzo)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

## What is CORTEX?

**CORTEX** is a desktop intelligence platform that turns any pile of files into an interactive knowledge graph. Think **Maltego meets Palantir** — but offline, $29 one-time, and runs on your machine with zero cloud dependencies.

- 🔍 **Autonomous file hunting** — point it at a folder, it reads every file
- 🧬 **Entity extraction** — regex-powered pattern matching (people, IPs, emails, crypto, etc.)
- 🕸️ **Interactive graph** — D3.js force-directed visualization with search, filter, export
- 📦 **Domain packs** — JSON configs that make CORTEX a specialist for any industry
- 🔒 **100% offline** — your data never leaves your machine

## This Pack

The **OSINT Starter Pack** (`osint.json`) transforms CORTEX into an open-source intelligence investigator:

### 26 Entity Types
| Entity | Example |
|--------|---------|
| Person | `John Smith`, `Dr. Jane Doe` |
| Organization | `Acme Corp`, `CIA` |
| Email | `user@domain.com` |
| Phone | `+1-555-0123` |
| IP Address | `192.168.1.1`, `2001:db8::1` |
| Domain | `example.com` |
| URL | `https://target.com/page` |
| Crypto Wallet | BTC, ETH, XMR addresses |
| Social Media | `@handle`, profile URLs |
| Vehicle Plate | `ABC-1234` |
| IMEI | Device identifiers |
| MAC Address | `00:1A:2B:3C:4D:5E` |
| Geolocation | `40.7128, -74.0060` |
| File Hash | MD5, SHA-1, SHA-256 |
| Dark Web | `.onion` addresses |
| Username | Online handles |
| IBAN | International bank accounts |
| Passport | Document numbers |
| ...and 8 more | |

### 15 Evidence Categories
Leaked Data, Social Engineering, Digital Forensics, Network Analysis, Financial Investigation, Physical Surveillance, Geospatial, Communications, Open Source, Human Intelligence, Dark Web, Cyber, Legal/Regulatory, Technical, Media

### 8 Focus Modes
`person_trace`, `network_map`, `financial`, `cyber`, `geospatial`, `dark_web`, `corporate`, `counter_intel`

## Quick Start

1. **[Download CORTEX Pro](https://andrewpioneer6.gumroad.com/l/cjamvzo)** ($29 one-time — includes app + 3 packs)
2. Drop `osint.json` into the `domains/` folder
3. Run: `cortex.exe hunt --domain osint --path C:\your\files`
4. View the graph: `cortex.exe view`

Or use the free version with just this pack:
```bash
cortex.exe list-domains         # See available packs
cortex.exe build --domain osint --path C:\investigation\files
cortex.exe view                 # Opens interactive D3.js graph
```

## 55 Domain Packs Available

The OSINT Starter is just the beginning. CORTEX has **55 domain packs** covering:

| Domain | Domain | Domain |
|--------|--------|--------|
| 🕵️ OSINT (FREE) | 🛡️ Cybersecurity | ⚖️ Legal |
| 💰 Fraud Investigation | 📰 Journalism | 🏥 Healthcare Fraud |
| 🏗️ Construction | 🚢 Maritime & Shipping | ✈️ Aviation Safety |
| 🎰 Casino & Gaming | 🏛️ Government Contracts | 🌍 Environmental |
| 💊 Pharmaceutical | 🔬 Academic Integrity | 🏘️ Real Estate |
| ...and 40 more | | |

**[Get all 55 packs for $79](https://andrewpioneer6.gumroad.com/l/cjamvzo)** (94% off individual pricing)

## Why CORTEX?

| Feature | CORTEX | Maltego | i2 ANB | Palantir |
|---------|--------|---------|--------|----------|
| **Price** | $29 | $5,000/yr | $8,000+ | $$$$$ |
| **Offline** | ✅ 100% | Partial | Yes | No |
| **Domain Packs** | 55 | Limited | Limited | Custom |
| **Autonomous Hunt** | ✅ | ❌ | ❌ | Partial |
| **No API Keys** | ✅ | ❌ | N/A | ❌ |

## License

This OSINT Starter Pack is released under the [MIT License](LICENSE). Use it freely.

The CORTEX application and premium domain packs are commercial products — [learn more](https://fatcrapinmybutt.github.io/cortex-site/).

---

**Built by investigators, for investigators.**

🌐 [Website](https://fatcrapinmybutt.github.io/cortex-site/) · 🛒 [Gumroad Store](https://andrewpioneer6.gumroad.com/l/cjamvzo)
