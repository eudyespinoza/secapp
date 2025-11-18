"""
Django management command to safely migrate chat schema from old to new version.

This command handles the migration from the old chat schema to the new professional
chat system by detecting existing tables and performing safe migration.

Usage:
    python manage.py migrate_chat_schema
    python manage.py migrate_chat_schema --force  # Force recreation even if tables exist
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Safely migrate chat schema from old to new version'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of all chat tables (deletes existing data)',
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Only check if migration is needed, do not perform it',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        check_only = options.get('check_only', False)

        self.stdout.write(self.style.MIGRATE_HEADING('Chat Schema Migration Tool'))
        self.stdout.write('=' * 70)

        # Check current state
        tables = self.get_chat_tables()
        
        if not tables:
            self.stdout.write(self.style.SUCCESS('✓ No chat tables found. Fresh installation detected.'))
            if not check_only:
                self.stdout.write('Applying chat migrations...')
                call_command('migrate', 'chat', verbosity=1)
                self.stdout.write(self.style.SUCCESS('✓ Chat tables created successfully!'))
            return

        # Check if we have the new schema
        new_schema = self.has_new_schema(tables)
        old_schema = self.has_old_schema(tables)

        self.stdout.write(f'\nFound {len(tables)} chat tables:')
        for table in sorted(tables):
            self.stdout.write(f'  - {table}')

        if new_schema and not old_schema:
            self.stdout.write(self.style.SUCCESS('\n✓ New chat schema already in place. No migration needed.'))
            return

        if old_schema and not new_schema:
            self.stdout.write(self.style.WARNING('\n⚠ Old chat schema detected. Migration required.'))
            migration_needed = True
        elif old_schema and new_schema:
            self.stdout.write(self.style.WARNING('\n⚠ Mixed schema detected (old + new tables). Cleanup required.'))
            migration_needed = True
        else:
            self.stdout.write(self.style.WARNING('\n⚠ Unknown schema state. Manual review recommended.'))
            migration_needed = True

        if check_only:
            if migration_needed:
                self.stdout.write(self.style.WARNING('\n✗ Migration needed but --check-only flag is set.'))
                return
            else:
                self.stdout.write(self.style.SUCCESS('\n✓ No migration needed.'))
                return

        # Perform migration
        if migration_needed or force:
            if force:
                self.stdout.write(self.style.WARNING('\n⚠ FORCE mode enabled. All chat data will be deleted.'))
            else:
                self.stdout.write(self.style.WARNING('\n⚠ Migration will delete existing chat data.'))
            
            # In production, require explicit confirmation
            import os
            if os.environ.get('DJANGO_ENV') == 'production' and not force:
                confirm = input('\nType "yes" to confirm migration: ')
                if confirm.lower() != 'yes':
                    self.stdout.write(self.style.ERROR('Migration cancelled.'))
                    return

            self.stdout.write('\nStep 1: Dropping old chat tables...')
            self.drop_old_tables(tables)
            self.stdout.write(self.style.SUCCESS('✓ Old tables dropped'))

            self.stdout.write('\nStep 2: Unmarking migrations...')
            call_command('migrate', 'chat', 'zero', '--fake', verbosity=0)
            self.stdout.write(self.style.SUCCESS('✓ Migrations unmarked'))

            self.stdout.write('\nStep 3: Creating new schema...')
            call_command('migrate', 'chat', verbosity=1)
            self.stdout.write(self.style.SUCCESS('✓ New schema created'))

            self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
            self.stdout.write(self.style.SUCCESS('✓ Chat migration completed successfully!'))
            self.stdout.write(self.style.SUCCESS('=' * 70))

    def get_chat_tables(self):
        """Get list of existing chat tables."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'chat_%'
                ORDER BY table_name
            """)
            return [row[0] for row in cursor.fetchall()]

    def has_new_schema(self, tables):
        """Check if new schema tables exist."""
        new_tables = {
            'chat_chatconversation',
            'chat_chatparticipant',
            'chat_chatmessage',
            'chat_chatmessagedelivery',
            'chat_chatattachment',
            'chat_userpresence',
        }
        return new_tables.issubset(set(tables))

    def has_old_schema(self, tables):
        """Check if old schema tables exist."""
        old_tables = {
            'chat_chatmessagemention',
            'chat_chatmessagereaction',
            'chat_chattypingindicator',
            'chat_chatconversation_participants',  # Old many-to-many table
        }
        return bool(old_tables.intersection(set(tables)))

    def drop_old_tables(self, tables):
        """Drop all chat tables in correct order (respecting foreign keys)."""
        # Define drop order (child tables first, parent tables last)
        drop_order = [
            'chat_chatmessagemention',
            'chat_chatmessagereaction',
            'chat_chattypingindicator',
            'chat_chatmessagedelivery',
            'chat_chatattachment',
            'chat_chatmessage',
            'chat_chatparticipant',
            'chat_chatconversation_participants',
            'chat_chatconversation',
            'chat_userpresence',
        ]

        with connection.cursor() as cursor:
            for table in drop_order:
                if table in tables:
                    self.stdout.write(f'  Dropping {table}...')
                    cursor.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
