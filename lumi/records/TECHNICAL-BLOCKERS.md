# Technical Blockers
| # | Blocker | Class | Evidence | Resolution path |
|---|---|---|---|---|
| 1 | Windows workspace C:\Users\fract\Documents\Codex\LumiStudioGlobal unreachable | Environmental | This session runs in a cloud Linux container; Desktop Commander reports platform=linux, no Windows mounts | Owner: push the folder (or screenplay + shot plan + outputs/*.md) to rogemaxi/rogemaxi, or upload files; OR run this repo's scripts in Claude Code on the Windows PC |
| 2 | Episode 1 screenplay / Shot 07 spec unavailable | Environmental | same | Same as #1 — needed before contact test |
| 3 | Lumi Global MCP not inspectable | Environmental | same | Not needed for animation; scripts run with Python + ffmpeg only |
Resolved this session: PIL float blur unsupported → numpy box blur; PIL floodfill no-op on array-backed image → .copy(); grey edge fringe from un-premultiply → keep original edge colours; matte speckles → main-component filter.
