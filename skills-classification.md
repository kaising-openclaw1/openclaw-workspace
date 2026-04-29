# OpenClaw Skills Classification (v2026.3.23)

**Total:** 51 skills

---

## 📊 By Category

### 1. Communication & Messaging (8 skills)
| Skill | Emoji | Platform | Description |
|-------|-------|----------|-------------|
| `bluebubbles` | 🫧 | iMessage | iMessage via BlueBubbles (recommended) |
| `imsg` | 📨 | iMessage | iMessage/SMS via macOS Messages.app |
| `discord` | 🎮 | Discord | Discord operations via message tool |
| `slack` | 💬 | Slack | Slack reactions, pins, messages |
| `himalaya` | 📧 | Email | IMAP/SMTP email CLI |
| `gog` | 🎮 | Google | Gmail, Calendar, Drive, Contacts, Sheets, Docs |
| `xurl` | 🐦 | X/Twitter | X API v2 (tweets, DMs, search) |
| `wacli` | 📱 | WhatsApp | WhatsApp messaging (business/API) |

### 2. Media, Audio & Video (9 skills)
| Skill | Emoji | Purpose |
|-------|-------|---------|
| `sag` | 🔊 | ElevenLabs TTS with local playback |
| `sherpa-onnx-tts` | 🔉 | Local offline TTS (no cloud) |
| `openai-whisper` | 🎤 | Local speech-to-text (Whisper CLI) |
| `openai-whisper-api` | 🌐 | OpenAI Whisper API transcription |
| `songsee` | 🌊 | Audio spectrograms & feature visualization |
| `video-frames` | 🎬 | Extract frames/clips from videos (ffmpeg) |
| `camsnap` | 📸 | RTSP/ONVIF camera snapshots & clips |
| `gifgrep` | 🧲 | Search/download GIFs, extract stills |
| `voice-call` | 📞 | Voice calls (Twilio, Telnyx, Plivo) |

### 3. Smart Home & IoT (5 skills)
| Skill | Emoji | Platform |
|-------|-------|----------|
| `openhue` | 💡 | Philips Hue lights & scenes |
| `sonoscli` | 🔊 | Sonos speakers |
| `blucli` | 🫐 | BluOS (Bluesound/NAD players) |
| `eightctl` | 🛌 | Eight Sleep pods (temp, alarms) |
| `canvas` | 🖼️ | Display HTML on OpenClaw nodes |

### 4. Productivity & Notes (8 skills)
| Skill | Emoji | Platform |
|-------|-------|----------|
| `obsidian` | 💎 | Obsidian vaults (Markdown notes) |
| `bear-notes` | 🐻 | Bear notes via grizzly CLI |
| `apple-notes` | 📝 | Apple Notes via memo CLI |
| `things-mac` | ✅ | Things 3 tasks/projects |
| `apple-reminders` | ⏰ | Apple Reminders via remindctl |
| `notion` | 📝 | Notion API (pages, databases) |
| `trello` | 📋 | Trello boards, lists, cards |
| `summarize` | 🧾 | Summarize URLs, files, podcasts |

### 5. Development & Coding (6 skills)
| Skill | Emoji | Purpose |
|-------|-------|---------|
| `coding-agent` | 🧩 | Delegate to Codex/Claude/Pi agents |
| `github` | 🐙 | GitHub CLI (issues, PRs, CI) |
| `gh-issues` | 🐛 | Auto-fix GitHub issues with sub-agents |
| `oracle` | 🧿 | Prompt + file bundling for LLM queries |
| `mcporter` | 📦 | MCP server/tool management |
| `tmux` | 🧵 | Remote-control tmux sessions |

### 6. System & Infrastructure (6 skills)
| Skill | Emoji | Purpose |
|-------|-------|---------|
| `healthcheck` | 🛡️ | Host security hardening & audits |
| `node-connect` | 📡 | Diagnose node connection/pairing |
| `session-logs` | 📜 | Search session conversation history |
| `model-usage` | 📊 | CodexBar cost/usage tracking |
| `1password` | 🔐 | 1Password CLI (secrets management) |
| `skill-creator` | 🛠️ | Create/edit/audit AgentSkills |

### 7. Web & Location (3 skills)
| Skill | Emoji | Purpose |
|-------|-------|---------|
| `weather` | ☔ | Weather via wttr.in / Open-Meteo |
| `goplaces` | 📍 | Google Places API (search, details) |
| `blogwatcher` | 📰 | Monitor blogs/RSS/Atom feeds |

### 8. Entertainment & Lifestyle (4 skills)
| Skill | Emoji | Purpose |
|-------|-------|---------|
| `spotify-player` | 🎵 | Spotify playback/search (spogo/spotify_player) |
| `ordercli` | 🛵 | Foodora order tracking |
| `peekaboo` | 👀 | macOS UI automation & screenshots |
| `gemini` | ✨ | Gemini CLI (one-shot Q&A) |

### 9. Utility & Tools (2 skills)
| Skill | Emoji | Purpose |
|-------|-------|---------|
| `nano-pdf` | 📄 | PDF editing with natural language |
| `clawhub` | 📦 | Skill marketplace (search/install/publish) |

---

## 📈 By Installation Method

| Method | Count | Skills |
|--------|-------|--------|
| **Homebrew** | 28 | summarize, camsnap, video-frames, goplaces, oracle, gifgrep, himalaya, imsg, obsidian, openhue, github, apple-reminders, openai-whisper, 1password, sag, xurl, weather, apple-notes, gemini, bear-notes (via go), ordercli, peekaboo, nano-pdf (via uv), wacli |
| **Go** | 10 | sonoscli, blucli, eightctl, blogwatcher, bear-notes, things-mac, gifgrep (alt), ordercli (alt), wacli (alt) |
| **Node/npm** | 5 | oracle, mcporter, clawhub, xurl (alt) |
| **Built-in/Config** | 8 | bluebubbles, discord, slack, voice-call, canvas, session-logs, model-usage, skill-creator, healthcheck, node-connect, notion, trello, openai-whisper-api, sherpa-onnx-tts, coding-agent, tmux, summarize |

---

## 🎯 By Platform Support

| Platform | Skills |
|----------|--------|
| **macOS only** | imsg, peekaboo, bear-notes, apple-notes, things-mac, apple-reminders, model-usage |
| **Cross-platform** | Most CLI tools (Linux/macOS) |
| **Config-based** | bluebubbles, discord, slack, voice-call, canvas, node-connect |

---

## 🔑 By API Key Requirements

| Skill | Required Env |
|-------|-------------|
| `goplaces` | `GOOGLE_PLACES_API_KEY` |
| `sag` | `ELEVENLABS_API_KEY` |
| `notion` | `NOTION_API_KEY` |
| `openai-whisper-api` | `OPENAI_API_KEY` |
| `trello` | `TRELLO_API_KEY`, `TRELLO_TOKEN` |
| `gh-issues` | `GH_TOKEN` |
| `sherpa-onnx-tts` | `SHERPA_ONNX_RUNTIME_DIR`, `SHERPA_ONNX_MODEL_DIR` |

---

## 📝 Notes

- **Most mature categories:** Communication (8), Media (9), Productivity (8)
- **Smallest categories:** Utility (2), Web (3)
- **Homebrew is the primary distribution method** (28/51 skills)
- **macOS-heavy:** Several skills are macOS-only due to Apple ecosystem integrations
- **Self-hosted focus:** Most skills use local CLI tools rather than cloud APIs
