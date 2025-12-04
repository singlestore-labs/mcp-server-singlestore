#!/usr/bin/env python3
"""
Test runner for remote mode authentication tests.

This script runs the complete test suite for remote authentication,
including unit tests and integration tests.
"""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run all remote authentication tests."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent

    # Test directories
    auth_test_dir = project_root / "tests" / "unit" / "auth"

    # Test files to run
    test_files = [
        "test_remote_auth_flow.py",
        "test_oauth_proxy_integration.py",
        "test_remote_api_auth.py",
    ]

    print("🧪 Running Remote Mode Authentication Tests")
    print("=" * 50)

    # Check if test files exist
    missing_files = []
    for test_file in test_files:
        if not (auth_test_dir / test_file).exists():
            missing_files.append(test_file)

    if missing_files:
        print(f"❌ Missing test files: {', '.join(missing_files)}")
        return 1

    # Run pytest for each test file
    failed_tests = []

    for test_file in test_files:
        test_path = auth_test_dir / test_file
        print(f"\n🔄 Running {test_file}...")

        try:
            # Run pytest with verbose output
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(test_path),
                    "-v",
                    "--tb=short",
                    "--color=yes",
                ],
                cwd=project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"✅ {test_file} passed")
                # Show summary of passed tests
                lines = result.stdout.split("\n")
                for line in lines:
                    if "passed" in line and ("failed" in line or "error" in line):
                        print(f"   {line.strip()}")
            else:
                print(f"❌ {test_file} failed")
                failed_tests.append(test_file)
                # Show error details
                print(f"STDOUT:\n{result.stdout}")
                print(f"STDERR:\n{result.stderr}")

        except Exception as e:
            print(f"💥 Error running {test_file}: {e}")
            failed_tests.append(test_file)

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)

    total_tests = len(test_files)
    passed_tests = total_tests - len(failed_tests)

    print(f"Total test files: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")

    if failed_tests:
        print(f"\n❌ Failed tests: {', '.join(failed_tests)}")
        return 1
    else:
        print("\n🎉 All tests passed!")
        return 0


def run_specific_test(test_name):
    """Run a specific test or test method."""
    project_root = Path(__file__).parent.parent.parent.parent
    auth_test_dir = project_root / "tests" / "unit" / "auth"

    print(f"🧪 Running specific test: {test_name}")
    print("=" * 50)

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(auth_test_dir),
                "-k",
                test_name,
                "-v",
                "--tb=long",
                "--color=yes",
            ],
            cwd=project_root,
        )

        return result.returncode

    except Exception as e:
        print(f"💥 Error running test {test_name}: {e}")
        return 1


def run_coverage():
    """Run tests with coverage reporting."""
    project_root = Path(__file__).parent.parent.parent.parent
    auth_test_dir = project_root / "tests" / "unit" / "auth"

    print("🧪 Running tests with coverage...")
    print("=" * 50)

    try:
        # Run pytest with coverage
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(auth_test_dir),
                "--cov=src.auth",
                "--cov=src.api.common",
                "--cov=src.config.config",
                "--cov-report=html",
                "--cov-report=term-missing",
                "-v",
            ],
            cwd=project_root,
        )

        if result.returncode == 0:
            print("\n📈 Coverage report generated in htmlcov/")

        return result.returncode

    except Exception as e:
        print(f"💥 Error running coverage: {e}")
        return 1


def main():
    """Main entry point for test runner."""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--coverage":
            return run_coverage()
        elif command == "--test":
            if len(sys.argv) > 2:
                return run_specific_test(sys.argv[2])
            else:
                print("❌ Please provide a test name: --test <test_name>")
                return 1
        elif command == "--help":
            print("Remote Auth Test Runner")
            print("Usage:")
            print("  python test_runner.py                    # Run all tests")
            print("  python test_runner.py --coverage         # Run with coverage")
            print("  python test_runner.py --test <name>      # Run specific test")
            print("  python test_runner.py --help             # Show this help")
            return 0
        else:
            print(f"❌ Unknown command: {command}")
            print("Use --help for usage information")
            return 1
    else:
        return run_tests()


if __name__ == "__main__":
    sys.exit(main())
