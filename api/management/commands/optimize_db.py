"""
Django management command for PostgreSQL database optimization.

Usage:
    python manage.py optimize_db           # Run all optimizations
    python manage.py optimize_db --analyze # Run ANALYZE only
    python manage.py optimize_db --vacuum  # Run VACUUM ANALYZE
    python manage.py optimize_db --indexes # Create performance indexes
"""

from django.core.management.base import BaseCommand
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Optimize PostgreSQL database for warranty system performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Run ANALYZE to update statistics',
        )
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Run VACUUM ANALYZE',
        )
        parser.add_argument(
            '--indexes',
            action='store_true',
            help='Create additional performance indexes',
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Check current table and index sizes',
        )

    def handle(self, *args, **options):
        # If no specific option, run all optimizations
        run_all = not any([
            options['analyze'],
            options['vacuum'],
            options['indexes'],
            options['check']
        ])

        with connection.cursor() as cursor:
            if options['check'] or run_all:
                self.check_sizes(cursor)

            if options['indexes'] or run_all:
                self.create_indexes(cursor)

            if options['analyze'] or run_all:
                self.run_analyze(cursor)

            if options['vacuum']:
                self.run_vacuum(cursor)

    def create_indexes(self, cursor):
        """Create additional performance indexes."""
        self.stdout.write('Creating performance indexes...')

        indexes = [
            # Case-insensitive asset name search
            """
            CREATE INDEX IF NOT EXISTS idx_warranty_asset_name_lower 
            ON api_warranty_registrations (LOWER(asset_name))
            """,
            
            # Case-insensitive serial number search
            """
            CREATE INDEX IF NOT EXISTS idx_warranty_serial_lower 
            ON api_warranty_registrations (LOWER(serial_number)) 
            WHERE serial_number IS NOT NULL
            """,
            
            # Partial index for active warranties
            """
            CREATE INDEX IF NOT EXISTS idx_warranty_active 
            ON api_warranty_registrations (warranty_end_date) 
            WHERE status = 'registered'
            """,
            
            # Registration date for date range queries
            """
            CREATE INDEX IF NOT EXISTS idx_warranty_registered_date 
            ON api_warranty_registrations (DATE(registered_at))
            """,
            
            # Composite index for common listing queries
            """
            CREATE INDEX IF NOT EXISTS idx_warranty_listing 
            ON api_warranty_registrations (status, registered_at DESC, department, category)
            """,
        ]

        # Try to create pg_trgm extension for fuzzy search
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            indexes.append("""
                CREATE INDEX IF NOT EXISTS idx_warranty_asset_name_gin 
                ON api_warranty_registrations USING gin (asset_name gin_trgm_ops)
            """)
            self.stdout.write(self.style.SUCCESS('  ✓ pg_trgm extension enabled'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ! Could not create pg_trgm extension: {e}'))

        for sql in indexes:
            try:
                cursor.execute(sql)
                index_name = sql.split('IF NOT EXISTS')[1].split('ON')[0].strip()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Index: {index_name}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {e}'))

        self.stdout.write(self.style.SUCCESS('Index creation completed.'))

    def run_analyze(self, cursor):
        """Run ANALYZE on warranty tables."""
        self.stdout.write('Running ANALYZE on warranty tables...')

        tables = [
            'api_warranty_registrations',
            'api_warranty_audit_log',
            'api_departments',
            'api_categories',
            'api_profiles',
        ]

        for table in tables:
            try:
                cursor.execute(f'ANALYZE {table}')
                self.stdout.write(self.style.SUCCESS(f'  ✓ Analyzed: {table}'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ! {table}: {e}'))

        self.stdout.write(self.style.SUCCESS('ANALYZE completed.'))

    def run_vacuum(self, cursor):
        """Run VACUUM ANALYZE on warranty tables."""
        self.stdout.write('Running VACUUM ANALYZE...')
        self.stdout.write(self.style.WARNING('  Note: This may take some time for large tables.'))

        # Need to set autocommit for VACUUM
        old_autocommit = connection.connection.autocommit
        connection.connection.autocommit = True

        tables = [
            'api_warranty_registrations',
            'api_warranty_audit_log',
        ]

        try:
            for table in tables:
                cursor.execute(f'VACUUM ANALYZE {table}')
                self.stdout.write(self.style.SUCCESS(f'  ✓ Vacuumed: {table}'))
        finally:
            connection.connection.autocommit = old_autocommit

        self.stdout.write(self.style.SUCCESS('VACUUM ANALYZE completed.'))

    def check_sizes(self, cursor):
        """Check table and index sizes."""
        self.stdout.write('\n=== Table Sizes ===')

        cursor.execute("""
            SELECT 
                relname AS table_name,
                pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
                pg_size_pretty(pg_relation_size(relid)) AS table_size,
                pg_size_pretty(pg_indexes_size(relid)) AS index_size
            FROM pg_catalog.pg_statio_user_tables
            WHERE relname LIKE 'api_%'
            ORDER BY pg_total_relation_size(relid) DESC
        """)

        rows = cursor.fetchall()
        if rows:
            self.stdout.write(f"{'Table':<40} {'Total':<12} {'Data':<12} {'Indexes':<12}")
            self.stdout.write('-' * 76)
            for row in rows:
                self.stdout.write(f"{row[0]:<40} {row[1]:<12} {row[2]:<12} {row[3]:<12}")
        else:
            self.stdout.write('No warranty tables found.')

        self.stdout.write('\n=== Index Usage Statistics ===')

        cursor.execute("""
            SELECT 
                indexname,
                idx_scan,
                idx_tup_read
            FROM pg_stat_user_indexes
            WHERE tablename LIKE 'api_%'
            ORDER BY idx_scan DESC
            LIMIT 15
        """)

        rows = cursor.fetchall()
        if rows:
            self.stdout.write(f"{'Index':<50} {'Scans':<12} {'Tuples Read':<12}")
            self.stdout.write('-' * 74)
            for row in rows:
                self.stdout.write(f"{row[0]:<50} {row[1]:<12} {row[2]:<12}")

        # Check for unused indexes
        cursor.execute("""
            SELECT indexname
            FROM pg_stat_user_indexes
            WHERE idx_scan = 0 
              AND tablename LIKE 'api_%'
              AND indexname NOT LIKE '%_pkey'
        """)

        unused = cursor.fetchall()
        if unused:
            self.stdout.write(self.style.WARNING('\n=== Unused Indexes (consider removing) ==='))
            for row in unused:
                self.stdout.write(f"  - {row[0]}")
