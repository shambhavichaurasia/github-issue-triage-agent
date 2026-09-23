import pytest

from src.github_tools import parse_repo


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("psf/requests", ("psf", "requests")),
        ("fastapi/fastapi", ("fastapi", "fastapi")),
        ("/owner/project/", ("owner", "project")),
    ],
)
def test_parse_repo_accepts_owner_and_name(
    value: str, expected: tuple[str, str]
) -> None:
    assert parse_repo(value) == expected


@pytest.mark.parametrize(
    "value",
    ["", "requests", "owner/repo/extra", "/repo"],
)
def test_parse_repo_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="owner/name"):
        parse_repo(value)
