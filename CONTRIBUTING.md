# Contributing to Exposome Compass

We welcome reproducible bug reports, environmental-source adapters, examples and methodological improvements.

1. File an issue describing software version, Python version, environment, expected versus actual result and a **small synthetic or redistributable** reproduction case. Never attach confidential research data, passwords or large copyrighted provider outputs.
2. Fork the repository and create a topic branch; avoid force-pushing shared branches.
3. Add deterministic tests for code changes and document changes to units, model assumptions, data contracts and output meanings. Use `python -m pytest -q`.
4. Keep environmental measurements separate from modelled decision weights. Do not invent defaults, silently drop missing postcodes, or claim epidemiological approval from numerical tests.
5. Request code and scientific review before changing transformations, relative indicator importance, correlation assumptions, source year policy or ranking denominators.

No automatic merge, release, paper attribution or model approval is promised.
