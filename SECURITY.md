# Security

## API credentials

This repository must never contain an OpenAI API key.

- `.env`, `.env.local`, and other `.env.*` files are ignored.
- `.env.example` is intentionally blank.
- The CLI reads `OPENAI_API_KEY` from the process environment and does not load,
  print, copy, or persist it.
- Generated run files include response IDs, tool observations, token use, and
  scores, but not request headers or credentials.

Before committing, scan the staged changes and confirm that only the blank
example is tracked:

```powershell
git diff --cached
git ls-files | Select-String -Pattern '^\.env'
```

If a key is ever committed, revoke it immediately in the OpenAI platform,
remove it from Git history, and replace it with a new key. Deleting it only from
the latest commit is not sufficient.

## Reporting

Please report a suspected credential exposure privately to the repository
owner. Do not open a public issue containing the credential.
