"""
The BrewCleaner GUI, split into mixins (v4.0).

App (in brewcleaner.py) inherits from every *Mixin class in this
package. Each file here is one section of what used to be a single
~2,600-line class body in brewcleaner.py, moved verbatim — see
ROADMAP.md for why this was done as its own pass, and
ui/_shared.py's docstring for how cross-cutting state (ctk, colors,
the package catalogue, prefs, etc.) is shared between them without
any circular imports.
"""
