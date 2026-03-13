#!/usr/bin/env python3

from click.testing import CliRunner

from pricetracker.cli import add_admin_user, add_worker_key, init_db_command, remove_test_data, generate_test_data


class TestAddAdminUser:

    def test_correct_call(self, test_app):
        """Happy path"""
        runner = CliRunner()
        result = runner.invoke(add_admin_user, ["test-admin-user@localhost"])
        assert result.exit_code == 0

    def test_no_parameter(self, test_app):
        """Missing parameter: email"""
        runner = CliRunner()
        result = runner.invoke(add_admin_user)
        assert result.exit_code == 2

    def test_duplicate_entry(self, test_app):
        """Already exists"""
        runner = CliRunner()
        result = runner.invoke(add_admin_user, ["test-admin-user@localhost"])
        assert result.exit_code == 0

        result = runner.invoke(add_admin_user, ["test-admin-user@localhost"])
        assert result.exit_code == 1


class TestAddWorkerKey:

    def test_correct_call(self, db_data):
        """Happy path"""
        runner = CliRunner()
        # Confirm that the db has been populated
        assert len(db_data['users']) > 0
        # Add worker key for all users
        for user in db_data["users"]:
            email = user.email
            result = runner.invoke(add_worker_key, [email])
            assert result.exit_code == 0

    def test_invalid_email(self, test_app):
        """Invalid email: does not exist"""
        runner = CliRunner()
        result = runner.invoke(add_worker_key, ["nonexistent-address@localhost"])
        assert result.exit_code == 1


class TestInitDB:
    """Test related to the CLI command which is used to initialize the database"""

    def test_correct_call(self, test_app):
        """Successful run"""
        runner = CliRunner()
        result = runner.invoke(init_db_command)
        assert result.exit_code == 0


class TestTestData:
    """These functions generate test data. Lets just make sure that they finish successfully"""

    def test_generate(self, test_app):
        """Successful run"""
        runner = CliRunner()
        result = runner.invoke(generate_test_data)
        assert result.exit_code == 0

    def test_remove(self, test_app):
        """Successful run"""
        runner = CliRunner()
        result = runner.invoke(remove_test_data)
        assert result.exit_code == 0
        result = runner.invoke(remove_test_data)
        assert result.exit_code == 0

    def test_duplicate(self, test_app):
        """Invoke two times in row"""
        runner = CliRunner()
        result = runner.invoke(generate_test_data)
        assert result.exit_code == 0
        result = runner.invoke(generate_test_data)
        assert result.exit_code == 1