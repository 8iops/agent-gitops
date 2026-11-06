import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parents[1]/"operations/releases"))
from select_accepted_releases import scope_matrix

def test_scope_preserves_default_and_selects_only_trusted_release():
    matrix = [{"release-id":"a"}, {"release-id":"b"}]
    assert scope_matrix(matrix, "") == matrix
    assert scope_matrix(matrix, "b") == [matrix[1]]
    with pytest.raises(ValueError, match="trusted replay matrix"):
        scope_matrix(matrix, "unknown")
