import os

# Directories to be created
DIRS = [
    "/var/tmp/youtility4_media",
    "/var/tmp/youtility4_logs",
    "/var/log/youtility4"
]

# Create directories and set permissions
for dir_path in DIRS:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
        os.chmod(dir_path, 0o755)
        os.chown(dir_path, os.getpwnam('redmine').pw_uid, os.getgrnam('redmine').gr_gid)

# Files to be touched (created if not present)
FILES = [
    "/var/log/youtility4/celery_b.err.log",
    "/var/log/youtility4/celery.err.log",
    "/var/log/youtility4/celery_b.log",
    "/var/log/youtility4/celery.log"
]

# Touch files and set permissions
for file_path in FILES:
    if not os.path.exists(file_path):
        open(file_path, 'a').close()  # Touch the file
        os.chmod(file_path, 0o644)
        os.chown(file_path, os.getpwnam('redmine').pw_uid, os.getgrnam('redmine').gr_gid)

print("Directories and log files set up successfully!")
