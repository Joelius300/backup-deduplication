# Backup deduplication

Simple Python script to deduplicate my backups. This was done mostly out of necessity and took less time than
switching to a different system altogether, which I might still do later on. It's designed to keep the latest backup
intact but remove instances of the same file in any previous backups, so they don't take up space. \
A log is written which should allow reconstruction of older backups if there is ever need for that (will very rarely
be the case for me). After deduplication, the older backups only contain the files that are not present in the newest
one and of course files that have changed between backups (then both backups keep their respective versions).

Run it with

```bash
python main.py deduplicate PATH
```

By default, it does a dry run for safety, use `--dry-run=False` to disable. It also assumes that it doesn't need to
check older backups (e.g. 2022) if the file exists in 2024 but not in 2023. To disable this,
use `--assume-continuity=False` (sometimes needed when copying together backups from different places).

Note, this is all very specific to my use case and setup. Use it as inspiration by all means but make sure it does what
YOU want it to before actually using it. \
Also note that it is designed to work in-places, so after the backup has been created. A more efficient way would be to
improve the backup process. Instead of first copying a file, then checking if any older backups contain that exact same
file and if so deleting it, you could also check if the file already exists in backup, move it to the new backup on disk
(instead of copying it across disks) and move on to the next file. This achieves the same in less time and with fewer
writes to the backup drive. However, this would bring additional complexity especially when working with different
file systems and would need integration with existing backup systems, so it's a lot more work to write
(hence the current, more naive implementation).

License: MIT
