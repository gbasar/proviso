"""Pipeline tests — action chaining, fail modes, nesting."""

from __future__ import annotations

from pathlib import Path

from proviso.actions import (
    ActionResult,
    ActionStatus,
    FailMode,
    GitSync,
    PackageInstall,
    Pipeline,
)
from proviso.providers import DnfProvider, PipProvider, ProviderRegistry
from proviso.provisions import PackageProvision
from proviso.shell import FakeShell, ShellResult

# --- Helpers ---


def _make_providers(shell: FakeShell) -> ProviderRegistry:
    reg = ProviderRegistry()
    reg.register(DnfProvider(shell=shell))
    reg.register(PipProvider(shell=shell))
    return reg


class _StubAction:
    """Minimal action for testing pipeline mechanics."""

    def __init__(self, name: str, status: ActionStatus = ActionStatus.SUCCESS) -> None:
        self._name = name
        self._status = status
        self.executed = False

    @property
    def action_name(self) -> str:
        return self._name

    def execute(self, provision: object) -> ActionResult:
        self.executed = True
        return ActionResult(
            status=self._status,
            action_name=self._name,
            resource_name=getattr(provision, "name", "unknown"),
            message=f"{self._name} done",
        )


# --- Tests ---


class TestPipelineBasic:
    def test_all_succeed(self) -> None:
        a1 = _StubAction("step-1")
        a2 = _StubAction("step-2")
        a3 = _StubAction("step-3")
        pipe = Pipeline(name="test-pipe", actions=[a1, a2, a3])
        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = pipe.execute(provision)

        assert result.status == ActionStatus.SUCCESS
        assert len(result.results) == 3
        assert all(r.status == ActionStatus.SUCCESS for r in result.results)
        assert result.pipeline_name == "test-pipe"
        assert result.resource_name == "jq"

    def test_empty_pipeline(self) -> None:
        pipe = Pipeline(name="empty", actions=[])
        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = pipe.execute(provision)

        assert result.status == ActionStatus.SUCCESS
        assert len(result.results) == 0


class TestFailFast:
    def test_stops_on_failure(self) -> None:
        a1 = _StubAction("step-1")
        a2 = _StubAction("step-2", ActionStatus.FAILED)
        a3 = _StubAction("step-3")
        pipe = Pipeline(name="test", actions=[a1, a2, a3], fail_mode=FailMode.FAST)
        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = pipe.execute(provision)

        assert result.status == ActionStatus.FAILED
        assert len(result.results) == 2  # a3 never ran
        assert not a3.executed

    def test_first_action_fails(self) -> None:
        a1 = _StubAction("step-1", ActionStatus.FAILED)
        a2 = _StubAction("step-2")
        pipe = Pipeline(name="test", actions=[a1, a2], fail_mode=FailMode.FAST)
        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = pipe.execute(provision)

        assert result.status == ActionStatus.FAILED
        assert len(result.results) == 1
        assert not a2.executed


class TestContinueMode:
    def test_continues_after_failure(self) -> None:
        a1 = _StubAction("step-1")
        a2 = _StubAction("step-2", ActionStatus.FAILED)
        a3 = _StubAction("step-3")
        pipe = Pipeline(name="test", actions=[a1, a2, a3], fail_mode=FailMode.CONTINUE)
        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = pipe.execute(provision)

        assert result.status == ActionStatus.FAILED
        assert len(result.results) == 3
        assert a3.executed
        assert result.results[0].status == ActionStatus.SUCCESS
        assert result.results[1].status == ActionStatus.FAILED
        assert result.results[2].status == ActionStatus.SUCCESS


class TestShapeMismatchInPipeline:
    def test_fail_fast_catches_shape_mismatch(self) -> None:
        shell = FakeShell()
        action = GitSync(shell=shell)  # expects SourceProvision
        a2 = _StubAction("after")
        pipe = Pipeline(name="test", actions=[action, a2], fail_mode=FailMode.FAST)

        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))
        result = pipe.execute(provision)

        assert result.status == ActionStatus.FAILED
        assert len(result.results) == 1
        msg = result.results[0].message
        assert "ShapeMismatchError" in msg or "SourceProvision" in msg
        assert not a2.executed

    def test_continue_mode_survives_shape_mismatch(self) -> None:
        shell = FakeShell()
        action = GitSync(shell=shell)
        a2 = _StubAction("after")
        pipe = Pipeline(name="test", actions=[action, a2], fail_mode=FailMode.CONTINUE)

        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))
        result = pipe.execute(provision)

        assert result.status == ActionStatus.FAILED
        assert len(result.results) == 2
        assert a2.executed


class TestNestedPipeline:
    def test_pipeline_in_pipeline(self) -> None:
        inner = Pipeline(
            name="inner",
            actions=[_StubAction("inner-1"), _StubAction("inner-2")],
        )
        outer = Pipeline(
            name="outer",
            actions=[_StubAction("outer-1"), inner, _StubAction("outer-3")],
        )
        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = outer.execute(provision)

        assert result.status == ActionStatus.SUCCESS
        assert len(result.results) == 3


class TestRealActionsInPipeline:
    def test_install_then_stub_log(self) -> None:
        shell = FakeShell(
            responses={
                "rpm -q jq": ShellResult(1),
                "dnf install -y jq": ShellResult(0),
            }
        )
        providers = _make_providers(shell)
        log = _StubAction("log")

        pipe = Pipeline(
            name="install-and-log",
            actions=[PackageInstall(providers=providers, shell=shell), log],
        )
        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = pipe.execute(provision)

        assert result.status == ActionStatus.SUCCESS
        assert len(result.results) == 2
        assert result.results[0].action_name == "package-install"
        assert log.executed
