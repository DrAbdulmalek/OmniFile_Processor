import argparse
from pathlib import Path

from config import Config
from src.migration import DataMigrator


def main():
    parser = argparse.ArgumentParser(description='Import bundled legacy seed data into the current project database.')
    parser.add_argument('--project-root', default='', help='Target project root. Defaults to Config.from_local().project_root')
    parser.add_argument('--base-path', default='legacy_seed', help='Folder that contains old projects like Handwriting_Dataset')
    parser.add_argument('--verified-only', action='store_true', default=False, help='Migrate verified rows only')
    args = parser.parse_args()

    if args.project_root:
        cfg = Config.from_local(project_root=args.project_root)
    else:
        cfg = Config.from_local()
    cfg.setup()

    migrator = DataMigrator(cfg)
    stats = migrator.migrate(base_path=args.base_path, verified_only=args.verified_only)
    print(stats)


if __name__ == '__main__':
    main()
