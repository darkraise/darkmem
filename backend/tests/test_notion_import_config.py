from app.config import settings
from app.services.events import EVENT_TYPES


def test_import_ceilings_have_their_documented_defaults():
    assert settings.notion_import_max_bytes == 1_073_741_824
    assert settings.notion_import_max_entries == 50_000
    assert settings.notion_import_max_uncompressed_bytes == 5_368_709_120
    assert settings.notion_import_max_pages == 10_000
    assert settings.notion_import_max_blocks == 250_000
    assert settings.notion_import_max_seconds == 900


def test_the_upload_ceiling_clears_the_real_export():
    # The measured export is 34.5 MB; a ceiling under it would refuse the one
    # archive this feature was designed against.
    assert settings.notion_import_max_bytes > 40 * 1024 * 1024


def test_pages_imported_is_in_the_event_vocabulary():
    assert "pages_imported" in EVENT_TYPES
