import re
import pytest

# Define which files are considered model files
MODEL_FILES = [
    "features/ingestion/models.py",
    "features/parsing/models.py",
    # Add more model files as needed
]

# Define forbidden DB session operations in model files
FORBIDDEN_SESSION_CALLS = ["session.commit", "session.add", "session.rollback"]

@pytest.mark.parametrize("filepath", MODEL_FILES)
def test_no_db_session_operations_in_models(filepath):
    assert os.path.exists(filepath), f"File not found: {filepath}"
    with open(filepath, "r") as f:
        content = f.read()
        for forbidden_call in FORBIDDEN_SESSION_CALLS:
            assert forbidden_call not in content, (
                f"❌ Forbidden DB call `{forbidden_call}` found in `{filepath}`. "
                "Move session logic to service or store layers."
            )
