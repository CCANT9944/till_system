"""Backup and restore helpers for the till database."""

from __future__ import annotations

import datetime
import shutil
import sqlite3
from pathlib import Path
from typing import Callable

BACKUP_DIR_NAME = "backups"
MANUAL_BACKUP_DIR_NAME = "manual"
AUTO_BACKUP_DIR_NAME = "auto"
RESTORE_SAFETY_BACKUP_DIR_NAME = "restore-safety"


class BackupService:
    def __init__(
        self,
        database_path: Path,
        get_connection: Callable[[], sqlite3.Connection],
        close_database: Callable[[], None],
        reconnect_database: Callable[[], None],
    ) -> None:
        self.database_path = database_path
        self._get_connection = get_connection
        self._close_database = close_database
        self._reconnect_database = reconnect_database

    @property
    def backup_dir(self) -> Path:
        return self.database_path.parent / BACKUP_DIR_NAME

    @property
    def manual_backup_dir(self) -> Path:
        return self.backup_dir / MANUAL_BACKUP_DIR_NAME

    @property
    def auto_backup_dir(self) -> Path:
        return self.backup_dir / AUTO_BACKUP_DIR_NAME

    @property
    def restore_safety_backup_dir(self) -> Path:
        return self.backup_dir / RESTORE_SAFETY_BACKUP_DIR_NAME

    def _get_backup_directory(self, kind: str) -> Path:
        if kind == "manual":
            return self.manual_backup_dir
        if kind == "auto":
            return self.auto_backup_dir
        if kind == "restore-safety":
            return self.restore_safety_backup_dir
        raise ValueError(f"Unsupported backup kind: {kind}")

    def _backup_sort_key(self, backup_path: Path) -> tuple[float, str]:
        return (backup_path.stat().st_mtime, backup_path.name)

    def _backup_glob(self) -> str:
        return f"{self.database_path.name}.*.bak"

    def _timestamped_backup_name(self) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S%fZ")
        return f"{self.database_path.name}.{timestamp}.bak"

    def _write_backup_file(self, destination: Path) -> Path:
        connection = self._get_connection()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination.unlink()
        backup_connection = sqlite3.connect(str(destination), timeout=5.0)
        try:
            connection.backup(backup_connection)
        finally:
            backup_connection.close()
        return destination

    def _list_backup_files(self, directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        return sorted(
            directory.glob(self._backup_glob()),
            key=self._backup_sort_key,
            reverse=True,
        )

    def _rotate_backup_directory(self, directory: Path, keep: int) -> None:
        backups = self._list_backup_files(directory)
        for old_backup in backups[keep:]:
            try:
                old_backup.unlink()
            except OSError:
                pass

    def create_timestamped_backup(self, keep: int = 14, *, kind: str = "manual") -> Path:
        if keep < 1:
            raise ValueError("keep must be at least 1.")

        backup_path = self._get_backup_directory(kind) / self._timestamped_backup_name()
        self._write_backup_file(backup_path)
        self._rotate_backup_directory(backup_path.parent, keep)
        return backup_path

    def list_backups(self, kinds: tuple[str, ...] = ("manual", "auto")) -> list[Path]:
        backups: list[Path] = []
        for kind in kinds:
            backups.extend(self._list_backup_files(self._get_backup_directory(kind)))
        return sorted(backups, key=self._backup_sort_key, reverse=True)

    def restore_from_backup(self, backup_path: Path) -> Path:
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError("Backup file not found.")

        self.restore_safety_backup_dir.mkdir(parents=True, exist_ok=True)
        safety_backup = self.restore_safety_backup_dir / (
            f"{self.database_path.name}.pre_restore."
            f"{datetime.datetime.now().strftime('%Y%m%dT%H%M%S%fZ')}.bak"
        )
        self._write_backup_file(safety_backup)
        self._rotate_backup_directory(self.restore_safety_backup_dir, keep=14)

        self._close_database()
        shutil.copyfile(str(backup_path), str(self.database_path))
        self._reconnect_database()
        return safety_backup