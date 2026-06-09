"""testing click functionality"""

from click.testing import CliRunner
from slackmoji.__main__ import main


def test_command_help() -> None:
    """test that something works using click"""
    runner = CliRunner()
    result = runner.invoke(
        main,
        args=[
            "--help",
        ],
    )
    assert result.exit_code == 0
    print(result)
