import itertools
from datetime import datetime
from pathlib import Path

import fire

DEFAULT_EXTENSIONS = ["jpg", "jpeg", "png", "tif", "bmp", "webp", "gif", "mp4", "mov", "txt", "md", "pdf",
                      "docx", "doc", "xlsx", "ods", "odt", "zip", "pptx", "apk", "enc", "exe", "mp3", "wav",
                      "opus", "m4a", "ipynb", "json", "csv", "tsv", "dic", "amr"]


def deduplicate(folder: str, dry_run=True, assume_continuity=True):
    folder = Path(folder)

    # get list of sub-folders sorted descending so 2024 is before 2023 (intended for YYYY-MM-DD)
    children = [f for f in sorted(folder.iterdir(), key=lambda f: f.name, reverse=True) if
                not f.name.endswith(".log.csv")]
    assert all(c.is_dir() for c in children), "not all children are directories"

    # we work under the assumption that the newer backups are a superset of the old ones and treat the
    # newest backup as the master backup. If anything in backup 2023 is also contained in the newest 2024,
    # it is deduplicated such that 2024 does not change and all the duplicates in 2023 or earlier are eliminated.
    # When a new update is added, e.g. 2025 and this script is re-run, everything in 2024 that is still in 2025 will be
    # removed. To restore the latest backup, just take it directly (it has not been altered). If you need to reconstruct
    # an older backup, take the backup from then and all non-conflicting files in the latest backup with a change date
    # prior to the backup date of the older backup. If change dates are missing, reconstruction might not be possible.
    # Since restoring the latest backup is much more common than reconstructing an older one, I'm doing it this way
    # and not the other way around where newer backups only contain the changes to the previous backups.
    # (Ps. I have to admit, just using some existing backup solution instead of doing it manually would be better.)

    # Example deduplication:
    # backup 2023 contains:         backup 2024 contains:
    # a                             -
    # b                             b
    # c (version 2022)              c (version 2024)
    # Then file b would be deleted from backup 2023 (and any previous backups).

    master_backup = children[0]
    older_backups = children[1:]

    master_files = itertools.chain.from_iterable(
        master_backup.glob("**/*." + ex, case_sensitive=False) for ex in DEFAULT_EXTENSIONS)
    master_files = (f.relative_to(master_backup) for f in master_files)

    bytes_freed = 0
    now = datetime.now()
    with open(folder / f"deduplication-{now.isoformat(timespec='seconds')}{('-dry' if dry_run else '')}.log.csv",
              "w") as reconstruction_log:
        reconstruction_log.write('alt_file;master_file;alt.st_ctime;master.st_ctime\n')
        for file in master_files:
            assert not file.is_absolute(), "Path is absolute, will fuck shit up"
            master_file = master_backup / file
            master_stats = master_file.stat()
            size = master_stats.st_size
            for backup in older_backups:
                alt_file = backup / file
                if not alt_file.exists():
                    # if the file from 2024 is not in backup 2023, we assume it also won't be in 2022 or earlier.
                    # in theory, the file could not change from 2000 to 2023 but from 2023 to 2024 and with this setup,
                    # none of the files from 2000 to 2024 would change. To improve this, you'd need to run the same
                    # algo for 2000 to 2022 with 2023 as the master instead of 2024 but the gains would probably
                    # be marginal as there are very few large files that change in my use case.
                    if assume_continuity:
                        break
                    else:
                        # if we disable this assumption (sometimes necessary), we just look through everything, even
                        # if it will be inefficient in many cases.
                        continue

                alt_stats = alt_file.stat()
                if alt_stats.st_size != size:
                    # file has changed from 2023 to 2024, we avoid the check 2022 against 2024 as they most likely
                    # won't be duplicates either.
                    if assume_continuity:
                        break
                    else:
                        # here it is almost safe to assume continuity and there will be extremely few cases where
                        # looking through everything is worth it but let's be consistent.
                        continue

                reconstruction_log.write(
                    f'"{alt_file.relative_to(folder)}";"{master_file.relative_to(folder)}";"{alt_stats.st_ctime}";"{master_stats.st_ctime}"\n')
                delete(alt_file, dry_run)
                bytes_freed += alt_stats.st_size

    # in all the older backups where files were removed, clean up the now empty folders.
    if not dry_run:
        for backup in older_backups:
            delete_empty_folders(backup)

    print(f"Freed {format_bytes(bytes_freed)}")


def format_bytes(size):
    power, n = 1024, 0
    power_labels = {0: 'bytes', 1: 'kb', 2: 'mb', 3: 'gb', 4: 'tb'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"


def delete_empty_folders(root: Path):
    deleted = set()

    for current_dir, subdirs, files in root.walk(top_down=False):
        still_has_subdirs = False
        for subdir in subdirs:
            if current_dir / subdir not in deleted:
                still_has_subdirs = True
                break

        if not any(files) and not still_has_subdirs:
            assert not any(current_dir.iterdir()), "Supposedly empty directory still contains file or subfolder!"
            print(f"Deleting empty directory '{current_dir}'")

            current_dir.rmdir()
            deleted.add(current_dir)

    return deleted


def delete(file: Path, dry_run: bool):
    print(f"Deleting '{file}'")

    if dry_run:
        return

    file.unlink()


if __name__ == '__main__':
    fire.Fire(dict(deduplicate=deduplicate))
