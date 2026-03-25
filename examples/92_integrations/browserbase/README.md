# BrowserBase Integration

A self-evolving web scraping agent powered by Convergence.

## What It Does

- Scrapes web pages using BrowserBase's cloud browser infrastructure
- Optimizes browser configuration: browser type, viewport, wait strategy, timeouts
- Learns which configurations maximize success rate and minimize execution time

## Full Implementation

See `examples/web_browsing/browserbase/` for the complete code:

- `browserbase_evaluator.py` -- Scores scraping results on success rate and speed

## Quick Start

```bash
export BROWSERBASE_API_KEY=your-key
python examples/web_browsing/browserbase/browserbase_evaluator.py
```
