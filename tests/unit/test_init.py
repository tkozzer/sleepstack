"""Tests for __init__.py"""

import pytest
from io import StringIO
from unittest.mock import patch

from sleepstack.__init__ import main


class TestInit:
    """Test the main function in __init__.py."""

    def test_main_function(self):
        """Test the main function outputs the expected message."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            main()

            output = mock_stdout.getvalue()
            assert output == "Hello from sleepstack!\n"
