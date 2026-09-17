from brewcleaner_pkg.snapshots import plan_restore


def test_plan_restore_only_adds_by_default():
    snap = {"formulae": ["a", "b"], "casks": ["x"]}
    plan = plan_restore(snap, installed_formulae=["b", "c"], installed_casks=[])
    assert plan.install_formulae == ["a"]
    assert plan.install_casks == ["x"]
    assert plan.remove_formulae == []
    assert plan.remove_casks == []


def test_plan_restore_can_remove_extras():
    snap = {"formulae": ["a"], "casks": []}
    plan = plan_restore(snap, installed_formulae=["a", "extra"], installed_casks=["extra-cask"],
                         remove_extras=True)
    assert plan.install_formulae == []
    assert plan.remove_formulae == ["extra"]
    assert plan.remove_casks == ["extra-cask"]


def test_plan_restore_noop_when_matching():
    snap = {"formulae": ["a"], "casks": []}
    plan = plan_restore(snap, installed_formulae=["a"], installed_casks=[])
    assert plan.is_noop
