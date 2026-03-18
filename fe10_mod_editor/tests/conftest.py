import os
import pytest

# Path to the project root (where Backup/, Game/ directories live)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP_DIR = os.path.join(PROJECT_ROOT, "Backup")
GAME_DATA_FILES = os.path.join(PROJECT_ROOT, "Game", "DATA", "files")
SHOP_DIR = os.path.join(GAME_DATA_FILES, "Shop")


@pytest.fixture
def backup_dir():
    """Path to the Backup directory containing original game files."""
    if not os.path.isdir(BACKUP_DIR):
        pytest.skip("Backup directory not found — need original game files for integration tests")
    return BACKUP_DIR


@pytest.fixture
def game_data_files():
    """Path to Game/DATA/files directory."""
    if not os.path.isdir(GAME_DATA_FILES):
        pytest.skip("Game data directory not found")
    return GAME_DATA_FILES


@pytest.fixture
def shop_dir():
    """Path to Game/DATA/files/Shop directory."""
    if not os.path.isdir(SHOP_DIR):
        pytest.skip("Shop directory not found")
    return SHOP_DIR
