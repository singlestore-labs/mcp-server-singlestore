from src.api.tools.notebooks import utils


class TestToolsNotebookUtils:
    def test_normalize_and_validate_schema(self):
        # Malformed notebook: missing metadata, cell with string source, extra cell type
        malformed_nb = {
            "cells": [
                {"type": "markdown", "content": "# Hello"},
                {"type": "code", "content": "print('ok')"},
                {"type": "raw", "content": "should be skipped"},
                {"type": "markdown"},  # missing content
            ]
        }
        normalized = utils.transform_to_valid_notebook_format(malformed_nb)
        schema_validated, schema_error = utils.validate_notebook_schema(normalized)
        assert schema_validated is True
        assert schema_error is None

    def test_minimal_valid_notebook(self):
        input_nb = {
            "cells": [
                {"type": "markdown", "content": "# Title"},
                {"type": "code", "content": "print('hi')"},
            ],
        }

        result = utils.transform_to_valid_notebook_format(input_nb)
        assert result["nbformat"] == 4
        assert result["nbformat_minor"] == 5
        assert "kernelspec" in result["metadata"]
        assert "language_info" in result["metadata"]
        assert len(result["cells"]) == 2
        assert result["cells"][0]["cell_type"] == "markdown"
        assert result["cells"][1]["cell_type"] == "code"
        assert isinstance(result["cells"][0]["source"], list)
        assert isinstance(result["cells"][1]["source"], list)

    def test_missing_metadata(self):
        input_nb = {"cells": [{"type": "markdown", "content": "foo"}]}
        result = utils.transform_to_valid_notebook_format(input_nb)
        assert "kernelspec" in result["metadata"]
        assert "language_info" in result["metadata"]

    def test_string_source(self):
        input_nb = {
            "cells": [
                {"type": "markdown", "content": "bar"},
                {"type": "code", "content": "baz"},
            ],
        }

        result = utils.transform_to_valid_notebook_format(input_nb)
        for cell in result["cells"]:
            assert isinstance(cell["source"], list)

    def test_missing_cell_fields(self):
        input_nb = {
            "cells": [
                {"type": "markdown"},  # missing content
                {"content": "no type"},  # missing type
                "not a dict",  # invalid cell
            ]
        }

        result = utils.transform_to_valid_notebook_format(input_nb)
        # Should skip invalid cells
        assert len(result["cells"]) == 0

    def test_extra_cell_type(self):
        input_nb = {
            "cells": [
                {"type": "raw", "content": "should be skipped"},
                {"type": "markdown", "content": "ok"},
            ]
        }

        result = utils.transform_to_valid_notebook_format(input_nb)
        assert len(result["cells"]) == 1
        assert result["cells"][0]["cell_type"] == "markdown"

    def test_already_valid_notebook(self):
        input_nb = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python"},
            },
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["hello"],
                },
                {
                    "id": "def456",
                    "cell_type": "code",
                    "metadata": {},
                    "source": ["print(1)"],
                    "outputs": [],
                    "execution_count": None,
                },
            ],
        }
        result = utils.transform_to_valid_notebook_format(input_nb)
        assert result["nbformat"] == 4
        assert result["nbformat_minor"] == 5
        assert len(result["cells"]) == 2
        assert result["cells"][0]["cell_type"] == "markdown"
        assert result["cells"][1]["cell_type"] == "code"
