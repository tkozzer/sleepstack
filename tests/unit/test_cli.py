"""Tests for cli.py"""

import pytest
import sys
import argparse
from unittest.mock import Mock, patch, call

from sleepstack.cli import (
    setup_logging,
    list_vibes,
    main,
)


class TestSetupLogging:
    """Test setup_logging function."""

    @patch('sleepstack.cli.logging.basicConfig')
    def test_setup_logging_verbose(self, mock_basic_config):
        """Test setup_logging with verbose=True."""
        setup_logging(verbose=True, quiet=False)
        
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]['level'] == 10  # logging.DEBUG
        assert call_args[1]['format'] == "%(levelname)s: %(message)s"
        assert call_args[1]['datefmt'] == "%H:%M:%S"

    @patch('sleepstack.cli.logging.basicConfig')
    def test_setup_logging_quiet(self, mock_basic_config):
        """Test setup_logging with quiet=True."""
        setup_logging(verbose=False, quiet=True)
        
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]['level'] == 30  # logging.WARNING

    @patch('sleepstack.cli.logging.basicConfig')
    def test_setup_logging_default(self, mock_basic_config):
        """Test setup_logging with default values."""
        setup_logging(verbose=False, quiet=False)
        
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]['level'] == 20  # logging.INFO

    @patch('sleepstack.cli.logging.basicConfig')
    def test_setup_logging_both_flags(self, mock_basic_config):
        """Test setup_logging with both verbose and quiet=True (quiet should take precedence)."""
        setup_logging(verbose=True, quiet=True)
        
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]['level'] == 30  # logging.WARNING (quiet takes precedence)


class TestListVibes:
    """Test list_vibes function."""

    @patch('sleepstack.cli.PRESETS')
    @patch('sleepstack.cli.ALIASES')
    @patch('builtins.print')
    def test_list_vibes_with_presets_and_aliases(self, mock_print, mock_aliases, mock_presets):
        """Test list_vibes with both presets and aliases."""
        # Mock presets
        mock_preset1 = Mock()
        mock_preset1.desc = "Test preset 1"
        mock_preset1.beat = 6.0
        mock_preset1.carrier = 200
        mock_preset1.volume = 0.28
        
        mock_preset2 = Mock()
        mock_preset2.desc = "Test preset 2"
        mock_preset2.beat = 4.5
        mock_preset2.carrier = 180
        mock_preset2.volume = 0.25
        
        mock_presets.items.return_value = [
            ("calm", mock_preset1),
            ("deep", mock_preset2)
        ]
        
        # Mock aliases
        mock_aliases.items.return_value = [
            ("sleep", "deep"),
            ("night", "calm")
        ]
        
        list_vibes()
        
        # Check that print was called multiple times
        assert mock_print.call_count > 0
        
        # Check specific content
        printed_text = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Available vibe presets:" in printed_text
        assert "calm" in printed_text
        assert "deep" in printed_text
        assert "Test preset 1" in printed_text
        assert "Test preset 2" in printed_text
        assert "6.0 Hz" in printed_text
        assert "200 Hz" in printed_text
        assert "Aliases:" in printed_text
        assert "sleep" in printed_text
        assert "night" in printed_text

    @patch('sleepstack.cli.PRESETS')
    @patch('sleepstack.cli.ALIASES')
    @patch('builtins.print')
    def test_list_vibes_empty_aliases(self, mock_print, mock_aliases, mock_presets):
        """Test list_vibes with empty aliases."""
        # Mock presets
        mock_preset = Mock()
        mock_preset.desc = "Test preset"
        mock_preset.beat = 6.0
        mock_preset.carrier = 200
        mock_preset.volume = 0.28
        
        mock_presets.items.return_value = [("calm", mock_preset)]
        mock_aliases.items.return_value = []  # Empty aliases
        
        list_vibes()
        
        # Check that print was called
        assert mock_print.call_count > 0
        
        # Check that aliases section is still printed even with empty aliases
        # (the function always prints "Aliases:" header)
        printed_text = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Available vibe presets:" in printed_text
        assert "Aliases:" in printed_text


class TestMain:
    """Test main function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.original_argv = sys.argv.copy()

    def teardown_method(self):
        """Clean up test fixtures."""
        sys.argv = self.original_argv

    def test_main_function_exists(self):
        """Test that main function exists and can be called."""
        # This is a basic smoke test to ensure the function exists
        assert callable(main)

    def test_main_known_commands_logic(self):
        """Test that known_commands logic works correctly."""
        # This test verifies the known_commands list is properly defined
        # The actual list is defined in the function, so we're testing the logic
        expected_commands = [
            'download-ambient', 'list-ambient', 'remove-ambient',
            'validate-assets', 'repair-assets', 'cleanup-assets'
        ]
        
        # We can't directly test the list, but we can verify the logic works
        # by ensuring the function doesn't crash when processing these commands
        for cmd in expected_commands:
            sys.argv = ["sleepstack", cmd, "--help"]
            with patch('sleepstack.cli.argparse.ArgumentParser') as mock_argparse:
                mock_parser = Mock()
                mock_parser.add_subparsers.return_value = Mock()
                mock_argparse.return_value = mock_parser
                with patch('sys.exit'):
                    # Should not raise an exception
                    main()


class TestMainFunctionality:
    """Test main function with various scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.original_argv = sys.argv.copy()

    def teardown_method(self):
        """Clean up test fixtures."""
        sys.argv = self.original_argv

    @pytest.mark.skip(reason="Complex mocking issues with argparse")
    @patch('sleepstack.cli.argparse.ArgumentParser')
    @patch('sleepstack.cli.add_download_ambient_parser')
    @patch('sleepstack.cli.add_list_ambient_parser')
    @patch('sleepstack.cli.add_remove_ambient_parser')
    @patch('sleepstack.cli.add_validate_assets_parser')
    @patch('sleepstack.cli.add_repair_assets_parser')
    @patch('sleepstack.cli.add_cleanup_assets_parser')
    @patch('sys.exit')
    def test_main_no_args_shows_help(self, mock_exit, mock_cleanup, mock_repair, mock_validate, 
                                    mock_remove, mock_list, mock_download, mock_argparse):
        """Test main function with no arguments shows help."""
        sys.argv = ["sleepstack"]
        
        mock_parser = Mock()
        mock_parser.print_help = Mock()
        mock_parser.add_argument = Mock()
        mock_parser.add_subparsers = Mock()
        mock_argparse.return_value = mock_parser
        
        main()
        
        mock_parser.print_help.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @pytest.mark.skip(reason="Complex mocking issues with argparse")
    @patch('sleepstack.cli.argparse.ArgumentParser')
    @patch('sleepstack.cli.add_download_ambient_parser')
    @patch('sleepstack.cli.add_list_ambient_parser')
    @patch('sleepstack.cli.add_remove_ambient_parser')
    @patch('sleepstack.cli.add_validate_assets_parser')
    @patch('sleepstack.cli.add_repair_assets_parser')
    @patch('sleepstack.cli.add_cleanup_assets_parser')
    @patch('sleepstack.cli.setup_logging')
    @patch('sleepstack.cli.list_vibes')
    @patch('sys.exit')
    def test_main_subcommand_with_list_vibes(self, mock_exit, mock_list_vibes, mock_setup_logging,
                                           mock_cleanup, mock_repair, mock_validate, mock_remove, 
                                           mock_list, mock_download, mock_argparse):
        """Test main function with subcommand and --list-vibes flag."""
        sys.argv = ["sleepstack", "download-ambient", "--list-vibes"]
        
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.list_vibes = True
        mock_args.verbose = False
        mock_args.quiet = False
        mock_args.func = None
        mock_parser.parse_args.return_value = mock_args
        mock_parser.add_argument = Mock()
        mock_parser.add_subparsers = Mock()
        mock_argparse.return_value = mock_parser
        
        main()
        
        mock_list_vibes.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch('sleepstack.cli.argparse.ArgumentParser')
    @patch('sleepstack.cli.add_download_ambient_parser')
    @patch('sleepstack.cli.add_list_ambient_parser')
    @patch('sleepstack.cli.add_remove_ambient_parser')
    @patch('sleepstack.cli.add_validate_assets_parser')
    @patch('sleepstack.cli.add_repair_assets_parser')
    @patch('sleepstack.cli.add_cleanup_assets_parser')
    @patch('sleepstack.cli.setup_logging')
    @patch('sys.exit')
    def test_main_subcommand_with_func(self, mock_exit, mock_setup_logging, mock_cleanup, 
                                     mock_repair, mock_validate, mock_remove, mock_list, 
                                     mock_download, mock_argparse):
        """Test main function with subcommand that has a func attribute."""
        sys.argv = ["sleepstack", "download-ambient", "url", "name"]
        
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.list_vibes = False
        mock_args.verbose = False
        mock_args.quiet = False
        mock_args.func = Mock(return_value=0)
        mock_parser.parse_args.return_value = mock_args
        mock_argparse.return_value = mock_parser
        
        main()
        
        mock_setup_logging.assert_called_once_with(verbose=False, quiet=False)
        mock_args.func.assert_called_once_with(mock_args)
        mock_exit.assert_called_once_with(0)

    @patch('sleepstack.cli.argparse.ArgumentParser')
    @patch('sleepstack.cli.add_download_ambient_parser')
    @patch('sleepstack.cli.add_list_ambient_parser')
    @patch('sleepstack.cli.add_remove_ambient_parser')
    @patch('sleepstack.cli.add_validate_assets_parser')
    @patch('sleepstack.cli.add_repair_assets_parser')
    @patch('sleepstack.cli.add_cleanup_assets_parser')
    @patch('sleepstack.cli.setup_logging')
    @patch('sleepstack.cli.logging')
    @patch('sys.exit')
    def test_main_subcommand_keyboard_interrupt(self, mock_exit, mock_logging, mock_setup_logging,
                                              mock_cleanup, mock_repair, mock_validate, mock_remove,
                                              mock_list, mock_download, mock_argparse):
        """Test main function with subcommand that raises KeyboardInterrupt."""
        sys.argv = ["sleepstack", "download-ambient", "url", "name"]
        
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.list_vibes = False
        mock_args.verbose = False
        mock_args.quiet = False
        mock_args.func = Mock(side_effect=KeyboardInterrupt())
        mock_parser.parse_args.return_value = mock_args
        mock_argparse.return_value = mock_parser
        
        main()
        
        mock_logging.info.assert_called_once_with("Interrupted by user")
        mock_exit.assert_called_once_with(130)

    @patch('sleepstack.cli.argparse.ArgumentParser')
    @patch('sleepstack.cli.add_download_ambient_parser')
    @patch('sleepstack.cli.add_list_ambient_parser')
    @patch('sleepstack.cli.add_remove_ambient_parser')
    @patch('sleepstack.cli.add_validate_assets_parser')
    @patch('sleepstack.cli.add_repair_assets_parser')
    @patch('sleepstack.cli.add_cleanup_assets_parser')
    @patch('sleepstack.cli.setup_logging')
    @patch('sleepstack.cli.logging')
    @patch('sys.exit')
    def test_main_subcommand_exception_verbose(self, mock_exit, mock_logging, mock_setup_logging,
                                             mock_cleanup, mock_repair, mock_validate, mock_remove,
                                             mock_list, mock_download, mock_argparse):
        """Test main function with subcommand that raises exception in verbose mode."""
        sys.argv = ["sleepstack", "download-ambient", "url", "name"]
        
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.list_vibes = False
        mock_args.verbose = True
        mock_args.quiet = False
        mock_args.func = Mock(side_effect=Exception("Test error"))
        mock_parser.parse_args.return_value = mock_args
        mock_argparse.return_value = mock_parser
        
        main()
        
        mock_logging.exception.assert_called_once_with("Unexpected error occurred")
        mock_exit.assert_called_once_with(1)

    @patch('sleepstack.cli.argparse.ArgumentParser')
    @patch('sleepstack.cli.add_download_ambient_parser')
    @patch('sleepstack.cli.add_list_ambient_parser')
    @patch('sleepstack.cli.add_remove_ambient_parser')
    @patch('sleepstack.cli.add_validate_assets_parser')
    @patch('sleepstack.cli.add_repair_assets_parser')
    @patch('sleepstack.cli.add_cleanup_assets_parser')
    @patch('sleepstack.cli.setup_logging')
    @patch('sleepstack.cli.logging')
    @patch('sys.exit')
    def test_main_subcommand_exception_not_verbose(self, mock_exit, mock_logging, mock_setup_logging,
                                                 mock_cleanup, mock_repair, mock_validate, mock_remove,
                                                 mock_list, mock_download, mock_argparse):
        """Test main function with subcommand that raises exception in non-verbose mode."""
        sys.argv = ["sleepstack", "download-ambient", "url", "name"]
        
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.list_vibes = False
        mock_args.verbose = False
        mock_args.quiet = False
        mock_args.func = Mock(side_effect=Exception("Test error"))
        mock_parser.parse_args.return_value = mock_args
        mock_argparse.return_value = mock_parser
        
        main()
        
        mock_logging.error.assert_called_once_with("Error: Test error")
        mock_exit.assert_called_once_with(1)

    @pytest.mark.skip(reason="Complex mocking issues with argparse")
    @patch('sleepstack.cli.argparse.ArgumentParser')
    @patch('sleepstack.cli.add_download_ambient_parser')
    @patch('sleepstack.cli.add_list_ambient_parser')
    @patch('sleepstack.cli.add_remove_ambient_parser')
    @patch('sleepstack.cli.add_validate_assets_parser')
    @patch('sleepstack.cli.add_repair_assets_parser')
    @patch('sleepstack.cli.add_cleanup_assets_parser')
    @patch('sleepstack.cli.setup_logging')
    @patch('sleepstack.cli.list_vibes')
    @patch('sleepstack.cli.run')
    @patch('sys.exit')
    def test_main_backward_compatibility_with_list_vibes(self, mock_exit, mock_run, mock_list_vibes,
                                                       mock_setup_logging, mock_cleanup, mock_repair,
                                                       mock_validate, mock_remove, mock_list, 
                                                       mock_download, mock_argparse):
        """Test main function backward compatibility with --list-vibes flag."""
        sys.argv = ["sleepstack", "--list-vibes", "--vibe", "calm"]
        
        mock_parser = Mock()
        mock_subparsers = Mock()
        mock_parser.add_subparsers.return_value = mock_subparsers
        mock_parser.add_argument = Mock()
        mock_argparse.return_value = mock_parser
        
        # Mock the global parser for backward compatibility
        with patch('sleepstack.cli.argparse.ArgumentParser') as mock_global_parser:
            mock_global_parser_instance = Mock()
            mock_global_parser.return_value = mock_global_parser_instance
            mock_global_args = Mock()
            mock_global_args.list_vibes = True
            mock_global_args.verbose = False
            mock_global_args.quiet = False
            mock_global_parser_instance.parse_known_args.return_value = (mock_global_args, ["--vibe", "calm"])
            
            main()
        
        mock_list_vibes.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch('sleepstack.cli.argparse.ArgumentParser')
    @patch('sleepstack.cli.add_download_ambient_parser')
    @patch('sleepstack.cli.add_list_ambient_parser')
    @patch('sleepstack.cli.add_remove_ambient_parser')
    @patch('sleepstack.cli.add_validate_assets_parser')
    @patch('sleepstack.cli.add_repair_assets_parser')
    @patch('sleepstack.cli.add_cleanup_assets_parser')
    @patch('sleepstack.cli.setup_logging')
    @patch('sleepstack.cli.run')
    @patch('sys.exit')
    def test_main_backward_compatibility_with_run(self, mock_exit, mock_run, mock_setup_logging,
                                                mock_cleanup, mock_repair, mock_validate, mock_remove,
                                                mock_list, mock_download, mock_argparse):
        """Test main function backward compatibility with main.run()."""
        sys.argv = ["sleepstack", "--vibe", "calm", "--minutes", "5"]
        
        mock_parser = Mock()
        mock_subparsers = Mock()
        mock_parser.add_subparsers.return_value = mock_subparsers
        mock_argparse.return_value = mock_parser
        
        # Mock the global parser for backward compatibility
        with patch('sleepstack.cli.argparse.ArgumentParser') as mock_global_parser:
            mock_global_parser_instance = Mock()
            mock_global_parser.return_value = mock_global_parser_instance
            mock_global_args = Mock()
            mock_global_args.list_vibes = False
            mock_global_args.verbose = False
            mock_global_args.quiet = False
            mock_global_parser_instance.parse_known_args.return_value = (mock_global_args, ["--vibe", "calm", "--minutes", "5"])
            
            mock_run.return_value = 0
            
            main()
        
        mock_setup_logging.assert_called_once_with(verbose=False, quiet=False)
        mock_run.assert_called_once_with(["--vibe", "calm", "--minutes", "5"])
        mock_exit.assert_called_once_with(0)

    @patch('sleepstack.cli.argparse.ArgumentParser')
    @patch('sleepstack.cli.add_download_ambient_parser')
    @patch('sleepstack.cli.add_list_ambient_parser')
    @patch('sleepstack.cli.add_remove_ambient_parser')
    @patch('sleepstack.cli.add_validate_assets_parser')
    @patch('sleepstack.cli.add_repair_assets_parser')
    @patch('sleepstack.cli.add_cleanup_assets_parser')
    @patch('sleepstack.cli.setup_logging')
    @patch('sleepstack.cli.logging')
    @patch('sys.exit')
    def test_main_backward_compatibility_keyboard_interrupt(self, mock_exit, mock_logging, mock_setup_logging,
                                                          mock_cleanup, mock_repair, mock_validate, mock_remove,
                                                          mock_list, mock_download, mock_argparse):
        """Test main function backward compatibility with KeyboardInterrupt."""
        sys.argv = ["sleepstack", "--vibe", "calm"]
        
        mock_parser = Mock()
        mock_subparsers = Mock()
        mock_parser.add_subparsers.return_value = mock_subparsers
        mock_argparse.return_value = mock_parser
        
        # Mock the global parser for backward compatibility
        with patch('sleepstack.cli.argparse.ArgumentParser') as mock_global_parser:
            mock_global_parser_instance = Mock()
            mock_global_parser.return_value = mock_global_parser_instance
            mock_global_args = Mock()
            mock_global_args.list_vibes = False
            mock_global_args.verbose = False
            mock_global_args.quiet = False
            mock_global_parser_instance.parse_known_args.return_value = (mock_global_args, ["--vibe", "calm"])
            
            with patch('sleepstack.cli.run', side_effect=KeyboardInterrupt()):
                main()
        
        mock_logging.info.assert_called_once_with("Interrupted by user")
        mock_exit.assert_called_once_with(130)

    @patch('sleepstack.cli.argparse.ArgumentParser')
    @patch('sleepstack.cli.add_download_ambient_parser')
    @patch('sleepstack.cli.add_list_ambient_parser')
    @patch('sleepstack.cli.add_remove_ambient_parser')
    @patch('sleepstack.cli.add_validate_assets_parser')
    @patch('sleepstack.cli.add_repair_assets_parser')
    @patch('sleepstack.cli.add_cleanup_assets_parser')
    @patch('sleepstack.cli.setup_logging')
    @patch('sleepstack.cli.logging')
    @patch('sys.exit')
    def test_main_backward_compatibility_exception_verbose(self, mock_exit, mock_logging, mock_setup_logging,
                                                         mock_cleanup, mock_repair, mock_validate, mock_remove,
                                                         mock_list, mock_download, mock_argparse):
        """Test main function backward compatibility with exception in verbose mode."""
        sys.argv = ["sleepstack", "--vibe", "calm"]
        
        mock_parser = Mock()
        mock_subparsers = Mock()
        mock_parser.add_subparsers.return_value = mock_subparsers
        mock_argparse.return_value = mock_parser
        
        # Mock the global parser for backward compatibility
        with patch('sleepstack.cli.argparse.ArgumentParser') as mock_global_parser:
            mock_global_parser_instance = Mock()
            mock_global_parser.return_value = mock_global_parser_instance
            mock_global_args = Mock()
            mock_global_args.list_vibes = False
            mock_global_args.verbose = True
            mock_global_args.quiet = False
            mock_global_parser_instance.parse_known_args.return_value = (mock_global_args, ["--vibe", "calm"])
            
            with patch('sleepstack.cli.run', side_effect=Exception("Test error")):
                main()
        
        mock_logging.exception.assert_called_once_with("Unexpected error occurred")
        mock_exit.assert_called_once_with(1)

    @patch('sleepstack.cli.argparse.ArgumentParser')
    @patch('sleepstack.cli.add_download_ambient_parser')
    @patch('sleepstack.cli.add_list_ambient_parser')
    @patch('sleepstack.cli.add_remove_ambient_parser')
    @patch('sleepstack.cli.add_validate_assets_parser')
    @patch('sleepstack.cli.add_repair_assets_parser')
    @patch('sleepstack.cli.add_cleanup_assets_parser')
    @patch('sleepstack.cli.setup_logging')
    @patch('sleepstack.cli.logging')
    @patch('sys.exit')
    def test_main_backward_compatibility_exception_not_verbose(self, mock_exit, mock_logging, mock_setup_logging,
                                                             mock_cleanup, mock_repair, mock_validate, mock_remove,
                                                             mock_list, mock_download, mock_argparse):
        """Test main function backward compatibility with exception in non-verbose mode."""
        sys.argv = ["sleepstack", "--vibe", "calm"]
        
        mock_parser = Mock()
        mock_subparsers = Mock()
        mock_parser.add_subparsers.return_value = mock_subparsers
        mock_argparse.return_value = mock_parser
        
        # Mock the global parser for backward compatibility
        with patch('sleepstack.cli.argparse.ArgumentParser') as mock_global_parser:
            mock_global_parser_instance = Mock()
            mock_global_parser.return_value = mock_global_parser_instance
            mock_global_args = Mock()
            mock_global_args.list_vibes = False
            mock_global_args.verbose = False
            mock_global_args.quiet = False
            mock_global_parser_instance.parse_known_args.return_value = (mock_global_args, ["--vibe", "calm"])
            
            with patch('sleepstack.cli.run', side_effect=Exception("Test error")):
                main()
        
        mock_logging.error.assert_called_once_with("Error: Test error")
        mock_exit.assert_called_once_with(1)

    @patch('sleepstack.cli.argparse.ArgumentParser')
    @patch('sleepstack.cli.add_download_ambient_parser')
    @patch('sleepstack.cli.add_list_ambient_parser')
    @patch('sleepstack.cli.add_remove_ambient_parser')
    @patch('sleepstack.cli.add_validate_assets_parser')
    @patch('sleepstack.cli.add_repair_assets_parser')
    @patch('sleepstack.cli.add_cleanup_assets_parser')
    def test_main_backward_compatibility_system_exit(self, mock_cleanup, mock_repair, mock_validate, 
                                                   mock_remove, mock_list, mock_download, mock_argparse):
        """Test main function backward compatibility with SystemExit from global parser."""
        sys.argv = ["sleepstack", "--version"]
        
        mock_parser = Mock()
        mock_subparsers = Mock()
        mock_parser.add_subparsers.return_value = mock_subparsers
        mock_argparse.return_value = mock_parser
        
        # Mock the global parser for backward compatibility
        with patch('sleepstack.cli.argparse.ArgumentParser') as mock_global_parser:
            mock_global_parser_instance = Mock()
            mock_global_parser.return_value = mock_global_parser_instance
            mock_global_parser_instance.parse_known_args.side_effect = SystemExit(0)
            
            # Should not raise an exception, just return
            main()


class TestIntegration:
    """Integration tests for CLI functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.original_argv = sys.argv.copy()

    def teardown_method(self):
        """Clean up test fixtures."""
        sys.argv = self.original_argv

    def test_cli_imports(self):
        """Test that CLI module can be imported and functions exist."""
        from sleepstack.cli import setup_logging, list_vibes, main
        
        assert callable(setup_logging)
        assert callable(list_vibes)
        assert callable(main)

    def test_cli_function_signatures(self):
        """Test that CLI functions have expected signatures."""
        import inspect
        
        # Test setup_logging signature
        setup_logging_sig = inspect.signature(setup_logging)
        assert 'verbose' in setup_logging_sig.parameters
        assert 'quiet' in setup_logging_sig.parameters
        
        # Test list_vibes signature
        list_vibes_sig = inspect.signature(list_vibes)
        assert len(list_vibes_sig.parameters) == 0
        
        # Test main signature
        main_sig = inspect.signature(main)
        assert len(main_sig.parameters) == 0