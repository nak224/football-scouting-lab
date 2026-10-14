from importlib import import_module


def test_package_can_be_imported():
    package = import_module("football_scouting_lab")

    assert package.__name__ == "football_scouting_lab"
