import pytest

from src.processing.profiles import get_profile


def test_get_profile_returns_known_profile() -> None:
    assert get_profile("prebuilt-layout").model_id == "prebuilt-layout"


def test_get_profile_rejects_unknown_model() -> None:
    with pytest.raises(ValueError, match="Unsupported model: unknown"):
        get_profile("unknown")


def test_every_profile_prompt_contains_data_placeholder() -> None:
    from src.processing.profiles import PROFILES

    assert all("{data}" in profile.prompt for profile in PROFILES.values())
