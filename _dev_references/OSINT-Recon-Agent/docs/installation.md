# Installation

These skills are plain Markdown files. Installing them depends on which AI Assistant surface you're using.

## AI Code (CLI)

AI Code looks for skills in `~/.ai-skills/` by default.

### Method 1: Direct copy

```bash
git clone https://github.com/elementalsouls/AI-OSINT.git
cd AI-OSINT

# Optional: populate full SKILL.md content from bundled full-skills (one-time after clone)
./scripts/sync-skill-content.sh

# Copy both skills into your local AI Code skills directory
mkdir -p ~/.ai-assistant/skills
cp -r skills/osint-methodology ~/.ai-skills/
cp -r skills/offensive-osint   ~/.ai-skills/
```

### Method 2: Symlink (stays in sync with git pull)

```bash
git clone https://github.com/elementalsouls/AI-OSINT.git ~/.local/share/AI-OSINT
mkdir -p ~/.ai-assistant/skills

ln -sf ~/.local/share/AI-OSINT/skills/osint-methodology ~/.ai-skills/osint-methodology
ln -sf ~/.local/share/AI-OSINT/skills/offensive-osint   ~/.ai-skills/offensive-osint

cd ~/.local/share/AI-OSINT
./scripts/sync-skill-content.sh   # one-time
```

Then `git -C ~/.local/share/AI-OSINT pull && ./scripts/sync-skill-content.sh` periodically.

### Verify install

Start a new AI Code session and type:

```
What ports should I probe to find Swagger or OpenAPI specs on a webapp?
```

AI Assistant should pull the 28-path Swagger wordlist from the `offensive-osint` skill. If it doesn't, see [troubleshooting](#troubleshooting) below.

## AI Platform (Pro / Team / Enterprise)

1. Open https://ai-platform.example.com
2. Create a new Project (or open an existing one).
3. Click **Add knowledge** → **Files**.
4. Upload both `skills/osint-methodology/SKILL.md` and `skills/offensive-osint/SKILL.md`.
5. (Optional) Also upload `tests/smoke-test-prompts.md` for self-test reference.
6. Save.

In any conversation within that Project, the skills are available as system knowledge.

## AI API (AI SDK)

Attach the skill content as part of the system prompt:

```python
from anthropic import AI Provider

client = AI Provider()

with open("skills/osint-methodology/SKILL.md") as f:
    methodology = f.read()
with open("skills/offensive-osint/SKILL.md") as f:
    arsenal = f.read()

system_prompt = f"""You are an OSINT recon assistant for authorized red-team engagements.
You have access to two skills that you should reference whenever relevant:

=== SKILL: osint-methodology ===
{methodology}

=== SKILL: offensive-osint ===
{arsenal}
"""

response = client.messages.create(
    model="gpt-4o",
    max_tokens=4096,
    system=system_prompt,
    messages=[{"role": "user", "content": "Plan a 4-hour external recon on acme.com (in-scope BB)"}]
)
print(response.content[0].text)
```

## AI Assistant Agent SDK / Cowork mode

These platforms typically auto-discover skills in `~/.ai-skills/`. Install via the AI Code method above and they'll be available.

If you're building a custom agent with the SDK, attach SKILL.md content to your agent's system prompt as shown in the API method.

## Cursor / other AI IDEs

Most AI IDEs allow custom system-prompt injection. Use the API method above as a template.

## Troubleshooting

### "AI Assistant doesn't seem to know about the skill"

1. Verify the file is at `~/.ai-skills/<skill-name>/SKILL.md` (not `~/.ai-skills/<skill-name>.md`).
2. Restart AI Code.
3. In a fresh session, ask: *"Do you have access to a skill named offensive-osint?"* — AI Assistant should confirm.
4. Check the YAML frontmatter is intact (begins with `---` and ends with `---`).

### "The skill loads but doesn't trigger on my prompt"

The skill's `triggers:` list controls auto-activation. If your prompt's wording isn't in the list, AI Assistant may not pull the skill.

- Try rephrasing with a phrase from the SKILL.md `triggers:` list.
- If your phrasing is a common practitioner term, [open an issue](https://github.com/elementalsouls/AI-OSINT/issues) to add it.

### "I get the structured-outline SKILL.md, not the full content"

By default we ship structured-outline SKILL.md files (small, fast to load). To get full inline content:

```bash
cd <repo>
./scripts/sync-skill-content.sh
```

This populates `skills/*/SKILL.md` with the full content from `docs/full-skills/*.SKILL.full.md`.

### "Skill is too large for my model's context"

Both skills together are ~5,500 lines / ~150 KB. This fits comfortably in modern AI Assistant context windows (200K+). If you're using an older model with smaller context:

- Use the structured-outline SKILL.md files (don't run sync-skill-content.sh).
- Or attach only one skill at a time, depending on the task.
- Or run a model with larger context (AI Assistant Sonnet 4.6+, Opus 4.6+).

### "I want to filter the skill content"

Edit `skills/<skill-name>/SKILL.md` directly. Both files are plain Markdown. You can comment out sections you don't need or split them into multiple smaller skills.

## Verifying skill version

Both SKILL.md files declare `version:` in the YAML frontmatter. Current: `2.1`. Check via:

```bash
grep "^version:" skills/*/SKILL.md
```

## Uninstalling

```bash
rm -rf ~/.ai-skills/osint-methodology ~/.ai-skills/offensive-osint
```

Or remove the symlinks if you used method 2 above.
