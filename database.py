"""MySQL connection helpers for StarNova."""

import os

import mysql.connector
from dotenv import load_dotenv

# Loads a local .env file when one exists. The file is not committed to Git.
load_dotenv()


def get_database_config():
    """Build MySQL settings from environment variables without connecting."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "starnova"),
    }


def get_connection():
    """Open and return a MySQL connection using the configured settings."""
    return mysql.connector.connect(**get_database_config())
