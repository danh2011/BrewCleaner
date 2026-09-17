"""
Snapshot diffing, pulled out of App._do_restore_snapshot so it can be
unit tested. The GUI (brewcleaner.py) still owns taking/listing/
deleting snapshots and running the actual `brew` commands — this
module only answers "given a snapshot and what's currently
installed, what needs to change?"

v4.0 addition: restore can now optionally remove packages that
aren't in the snapshot too (previously it could only ever add,
never remove — see prefs "restore_removes_extras").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class RestorePlan:
    install_formulae: List[str] = field(default_factory=list)
    install_casks: List[str] = field(default_factory=list)
    remove_formulae: List[str] = field(default_factory=list)
    remove_casks: List[str] = field(default_factory=list)

    @property
    def is_noop(self) -> bool:
        return not any((self.install_formulae, self.install_casks,
                         self.remove_formulae, self.remove_casks))


def plan_restore(
    snapshot: Dict,
    installed_formulae: List[str],
    installed_casks: List[str],
    remove_extras: bool = False,
) -> RestorePlan:
    snap_formulae = set(snapshot.get("formulae", []))
    snap_casks = set(snapshot.get("casks", []))
    have_formulae = set(installed_formulae)
    have_casks = set(installed_casks)

    plan = RestorePlan(
        install_formulae=sorted(snap_formulae - have_formulae),
        install_casks=sorted(snap_casks - have_casks),
    )
    if remove_extras:
        plan.remove_formulae = sorted(have_formulae - snap_formulae)
        plan.remove_casks = sorted(have_casks - snap_casks)
    return plan
