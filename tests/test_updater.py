"""Updater git-parsing logic, tested with a fake runner (no real git)."""

from flipperkit import updater


def make_run(mapping):
    def run(*args):
        return mapping.get(" ".join(args), (1, ""))
    return run


def test_is_git_repo():
    assert updater.is_git_repo(make_run({"rev-parse --is-inside-work-tree": (0, "true")})) is True
    assert updater.is_git_repo(make_run({"rev-parse --is-inside-work-tree": (128, "fatal")})) is False


def test_current_branch_and_detached_head():
    assert updater.current_branch(make_run({"rev-parse --abbrev-ref HEAD": (0, "main")})) == "main"
    assert updater.current_branch(make_run({"rev-parse --abbrev-ref HEAD": (0, "HEAD")})) is None


def test_ahead_behind_parses_output():
    run = make_run({"rev-list --left-right --count HEAD...origin/main": (0, "2\t5")})
    assert updater.ahead_behind(run, "main") == (2, 5)


def test_ahead_behind_none_on_error():
    assert updater.ahead_behind(make_run({}), "main") is None


def test_working_tree_dirty():
    assert updater.working_tree_dirty(make_run({"status --porcelain": (0, "")})) is False
    assert updater.working_tree_dirty(make_run({"status --porcelain": (0, " M x.py")})) is True


def test_remote_url():
    run = make_run({"remote get-url origin": (0, "https://github.com/juandresrodca/FlipperKit.git")})
    assert updater.remote_url(run) == "https://github.com/juandresrodca/FlipperKit.git"
    assert updater.remote_url(make_run({})) is None


_BASE = {
    "rev-parse --is-inside-work-tree": (0, "true"),
    "rev-parse --abbrev-ref HEAD": (0, "main"),
    "remote get-url origin": (0, "https://github.com/juandresrodca/FlipperKit.git"),
    "fetch origin --quiet": (0, ""),
    "status --porcelain": (0, ""),
    "rev-parse --short HEAD": (0, "abc1234"),
}


def test_check_up_to_date():
    mapping = {**_BASE, "rev-list --left-right --count HEAD...origin/main": (0, "0\t0")}
    status = updater.check(make_run(mapping))
    assert status.is_repo is True
    assert status.fetched is True
    assert status.behind == 0
    assert status.local == "abc1234"
    assert status.branch == "main"
    assert status.remote.endswith("FlipperKit.git")


def test_check_reports_behind_and_dirty():
    mapping = {
        **_BASE,
        "rev-list --left-right --count HEAD...origin/main": (0, "0\t3"),
        "status --porcelain": (0, " M src/flipperkit/cli.py"),
    }
    status = updater.check(make_run(mapping))
    assert status.behind == 3
    assert status.dirty is True


def test_check_flags_failed_fetch():
    # Fetch fails (e.g. offline) -> fetched False, so caller won't claim up-to-date.
    mapping = {**_BASE, "fetch origin --quiet": (128, "fatal: unable to access remote")}
    status = updater.check(make_run(mapping))
    assert status.fetched is False
    assert "unable to access" in status.fetch_error


def test_check_reports_not_a_repo():
    status = updater.check(make_run({"rev-parse --is-inside-work-tree": (128, "fatal")}))
    assert status.is_repo is False
