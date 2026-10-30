from modules.career_map import career_map_source, rank_career_paths


def test_career_map_connects_interest_and_lived_experience_to_roles() -> None:
    paths = rank_career_paths(
        ["I built a Python project to clean data, analyze trends, and explain findings with charts."],
        "I am curious about data science.",
        limit=12,
    )

    assert paths
    assert any(path["title"] == "Data Scientists" for path in paths)
    data_science_path = next(path for path in paths if path["title"] == "Data Scientists")
    assert data_science_path["tasks"]
    assert data_science_path["transferable_skills"]
    assert data_science_path["source_url"].startswith("https://www.onetonline.org/")
    assert "score" not in data_science_path


def test_career_map_does_not_invent_paths_for_no_story() -> None:
    assert rank_career_paths([], "I do not know yet") == []


def test_career_map_source_includes_open_license_attribution() -> None:
    source = career_map_source()
    assert source["name"] == "O*NET Database 31.0"
    assert source["license"] == "CC BY 4.0"
    assert source["license_url"].startswith("https://creativecommons.org/licenses/by/")
