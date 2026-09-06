from django.core.management.base import BaseCommand
from users.models import CustomUser
from django.db import connection


class Command(BaseCommand):
    help = 'Delete users'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Delete specific user')
        parser.add_argument('--filter', choices=['all', 'admins', 'superusers', 'users'], 
                           default='all', help='Filter users to delete (default: all)')
        parser.add_argument('--no-input', action='store_true', help='Skip confirmation')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted')

    def handle(self, *args, **options):
        if options['username']:
            self._delete_by_username(options['username'], options['dry_run'])
            return
        
        filter_map = {
            'admins': {'is_staff': True},
            'superusers': {'is_superuser': True},
            'users': {'is_staff': False, 'is_superuser': False},
            'all': {}
        }
        
        filters = filter_map.get(options['filter'], {})
        queryset = CustomUser.objects.filter(**filters)
        filter_name = options['filter']
        
        self._delete_queryset(queryset, filter_name, options)
    
    def _table_exists(self, table_name):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, [table_name])
            return cursor.fetchone()[0]
    
    def _safe_delete_user(self, user):
        user_id = user.id
        with connection.cursor() as cursor:
            if self._table_exists('django_admin_log'):
                cursor.execute('DELETE FROM django_admin_log WHERE user_id = %s', [user_id])
            if self._table_exists('users_customuser_groups'):
                cursor.execute('DELETE FROM users_customuser_groups WHERE customuser_id = %s', [user_id])
            if self._table_exists('users_customuser_user_permissions'):
                cursor.execute('DELETE FROM users_customuser_user_permissions WHERE customuser_id = %s', [user_id])
            if self._table_exists('users_usersettings'):
                cursor.execute('DELETE FROM users_usersettings WHERE user_id = %s', [user_id])
            cursor.execute('DELETE FROM users_customuser WHERE id = %s', [user_id])
    
    def _delete_by_username(self, username, dry_run):
        try:
            user = CustomUser.objects.get(username=username)
            if dry_run:
                self.stdout.write(f"[DRY RUN] Would delete: {username}")
            else:
                self._safe_delete_user(user)
                self.stdout.write(self.style.SUCCESS(f"Deleted: {username}"))
        except CustomUser.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User '{username}' not found"))
    
    def _delete_queryset(self, queryset, filter_name, options):
        count = queryset.count()
        if count == 0:
            self.stdout.write(f"No {filter_name} users found")
            return
        
        self.stdout.write(f"Found {count} {filter_name} users")
        
        if options['dry_run']:
            for user in queryset[:10]:
                self.stdout.write(f"  - {user.username}")
            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more")
            return
        
        if not options['no_input']:
            confirm = input(f"Delete {count} {filter_name} users? [y/N]: ")
            if confirm.lower() != 'y':
                self.stdout.write("Cancelled")
                return
        
        deleted = 0
        for user in queryset:
            try:
                self._safe_delete_user(user)
                deleted += 1
            except Exception as e:
                self.stderr.write(f"Failed: {user.username} - {e}")
        
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} users"))