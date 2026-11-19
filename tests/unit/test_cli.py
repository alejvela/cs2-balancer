import pytest

import cs2_balancer_cli as cli


@pytest.mark.parametrize(
    "argv,text",
    [
        (["--help"], "tournament-report"),
        (["balance", "--help"], "Balance a roster"),
        (["tournament-report", "--help"], "Generate a tournament report"),
    ],
)
def test_help(argv, text, capsys):
    assert cli.main(argv) == 0
    out, err = capsys.readouterr()
    assert text in out
    assert not err


@pytest.mark.parametrize(
    "argv,message",
    [
        ([], "required"),
        (["other"], "invalid choice"),
        (["--ver"], "unrecognized arguments"),
        (["balance", "--he"], "unrecognized arguments"),
        (["tournament-report", "--input", "data.csv"], "unrecognized arguments"),
        (["balance"], "balance is not available yet"),
        (["tournament-report"], "tournament-report is not available yet"),
    ],
)
def test_usage_errors(argv, message, capsys):
    assert cli.main(argv) == 2
    out, err = capsys.readouterr()
    assert not out
    assert "usage:" in err
    assert message in err


def test_version_uses_distribution_metadata(monkeypatch, capsys):
    def version(name):
        assert name == "cs2-balancer"
        return "1.2.3"

    monkeypatch.setattr(cli.metadata, "version", version)
    assert cli.main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "cs2-balancer 1.2.3"


def test_version_without_distribution_metadata(monkeypatch, capsys):
    def missing(name):
        raise cli.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(cli.metadata, "version", missing)
    assert cli.main(["--version"]) == 0
    assert "metadata unavailable" in capsys.readouterr().out
