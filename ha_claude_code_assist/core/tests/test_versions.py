import pytest

from ha_cca.versions import APP_OUTDATED, INTEGRATION_OUTDATED, IntegrationVersion, problem, problem_message


@pytest.mark.parametrize("app, integration, expected", [
    ("0.3.0", "0.3.0", None),
    ("0.3.0", "0.2.0", INTEGRATION_OUTDATED),
    ("0.3.0", None, INTEGRATION_OUTDATED),  # an integration before 0.3.0 reports no version
    ("0.10.0", "0.9.0", INTEGRATION_OUTDATED),  # compared as numbers, not as text
    ("0.3.0", "0.4.0", APP_OUTDATED),
    ("0.3.0", "0.3.1", APP_OUTDATED),
    (None, "0.3.0", None),  # the app's own version unknown: nothing to say
])
def test_which_side_is_out_of_date(app, integration, expected):
    assert problem(app, integration) == expected


def test_the_message_says_what_to_update():
    assert problem_message("0.3.0", "0.3.0") is None
    assert problem_message("0.3.0", "0.2.0") == (
        "The HA Claude Code Assist integration, version 0.2.0, is older than the app, version 0.3.0. "
        "Update the integration in the Marketplace or HACS, then restart Home Assistant.")
    assert problem_message("0.3.0", "0.4.0") == (
        "The HA Claude Code Assist app, version 0.3.0, is older than its integration, version 0.4.0. "
        "Update the app in Settings > Apps.")


def test_the_integrations_version_is_kept_across_restarts(tmp_path):
    path = tmp_path / "integration.json"
    first = IntegrationVersion(path)
    assert (first.known, first.version) == (False, None)
    assert first.report("0.3.0") is True
    assert first.report("0.3.0") is False  # nothing written when it did not change
    again = IntegrationVersion(path)
    assert (again.known, again.version) == (True, "0.3.0")


def test_an_integration_that_reports_no_version_is_known(tmp_path):
    version = IntegrationVersion(tmp_path / "integration.json")
    assert version.report(None) is True
    assert (version.known, version.version) == (True, None)
    assert version.report(None) is False


def test_the_message_for_an_integration_that_reports_no_version():
    assert problem_message("0.3.0", None) == (
        "The HA Claude Code Assist integration is older than the app, version 0.3.0. "
        "Update the integration in the Marketplace or HACS, then restart Home Assistant.")
