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
        normalized, error = utils.transform_to_valid_notebook_format(malformed_nb)
        assert error is None
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

        result, error = utils.transform_to_valid_notebook_format(input_nb)
        assert error is None
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
        result, error = utils.transform_to_valid_notebook_format(input_nb)
        assert error is None
        assert "kernelspec" in result["metadata"]
        assert "language_info" in result["metadata"]

    def test_string_source(self):
        input_nb = {
            "cells": [
                {"type": "markdown", "content": "bar"},
                {"type": "code", "content": "baz"},
            ],
        }

        result, error = utils.transform_to_valid_notebook_format(input_nb)
        assert error is None
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

        result, error = utils.transform_to_valid_notebook_format(input_nb)
        assert error is None
        # Should skip invalid cells
        assert len(result["cells"]) == 0

    def test_extra_cell_type(self):
        input_nb = {
            "cells": [
                {"type": "raw", "content": "should be skipped"},
                {"type": "markdown", "content": "ok"},
            ]
        }

        result, error = utils.transform_to_valid_notebook_format(input_nb)
        assert error is None
        assert len(result["cells"]) == 1
        assert result["cells"][0]["cell_type"] == "markdown"

    def test_code_cell_language_metadata_default(self):
        input_nb = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print('hi')"],
                    "outputs": [],
                    "execution_count": None,
                },
            ],
        }
        result, error = utils.transform_to_valid_notebook_format(input_nb)
        assert error is None
        assert result["cells"][0]["metadata"]["language"] == "python"

    def test_code_cell_language_metadata_explicit(self):
        input_nb = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["SELECT 1"],
                    "metadata": {"language": "sql"},
                    "outputs": [],
                    "execution_count": None,
                },
            ],
        }
        result, error = utils.transform_to_valid_notebook_format(input_nb)
        assert error is None
        assert result["cells"][0]["metadata"]["language"] == "sql"

    def test_code_cell_language_metadata_case_insensitive(self):
        input_nb = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["SELECT 1"],
                    "metadata": {"language": "SQL"},
                    "outputs": [],
                    "execution_count": None,
                },
            ],
        }
        result, error = utils.transform_to_valid_notebook_format(input_nb)
        assert error is None
        assert result["cells"][0]["metadata"]["language"] == "sql"

    def test_code_cell_empty_language_defaults_to_python(self):
        input_nb = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print('hi')"],
                    "metadata": {"language": ""},
                    "outputs": [],
                    "execution_count": None,
                },
            ],
        }
        result, error = utils.transform_to_valid_notebook_format(input_nb)
        assert error is None
        assert result["cells"][0]["metadata"]["language"] == "python"

    def test_transform_non_string_language_errors(self):
        input_nb = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print(1)"],
                    "metadata": {"language": 123},
                    "outputs": [],
                    "execution_count": None,
                },
            ],
        }
        _, error = utils.transform_to_valid_notebook_format(input_nb)
        assert error is not None
        assert error["errorCode"] == "INVALID_CELL_LANGUAGE"

    def test_transform_invalid_language_errors(self):
        input_nb = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["puts 'hi'"],
                    "metadata": {"language": "ruby"},
                    "outputs": [],
                    "execution_count": None,
                },
            ],
        }
        _, error = utils.transform_to_valid_notebook_format(input_nb)
        assert error is not None
        assert error["errorCode"] == "INVALID_CELL_LANGUAGE"

    def test_convert_to_notebook_cells_language(self):
        cells = [
            {"type": "code", "content": "SELECT 1", "language": "sql"},
            {"type": "code", "content": "print(1)"},
        ]
        notebook_cells, error = utils.convert_to_notebook_cells(cells)
        assert error is None
        assert notebook_cells[0]["metadata"]["language"] == "sql"
        assert notebook_cells[1]["metadata"]["language"] == "python"

    def test_convert_to_notebook_cells_empty_language_defaults_to_python(self):
        cells = [
            {"type": "code", "content": "print(1)", "language": ""},
        ]
        notebook_cells, error = utils.convert_to_notebook_cells(cells)
        assert error is None
        assert notebook_cells[0]["metadata"]["language"] == "python"

    def test_convert_to_notebook_cells_invalid_language(self):
        cells = [
            {"type": "code", "content": "x", "language": "ruby"},
        ]
        _, error = utils.convert_to_notebook_cells(cells)
        assert error is not None
        assert error["errorCode"] == "INVALID_CELL_LANGUAGE"

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
        result, error = utils.transform_to_valid_notebook_format(input_nb)
        assert error is None
        assert result["nbformat"] == 4
        assert result["nbformat_minor"] == 5
        assert len(result["cells"]) == 2
        assert result["cells"][0]["cell_type"] == "markdown"
        assert result["cells"][1]["cell_type"] == "code"
        assert result["cells"][1]["metadata"]["language"] == "python"
