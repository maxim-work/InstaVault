from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
User = get_user_model()


class Command(BaseCommand):
    help = 'Transfer owner rights to another user'
    
    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the new owner')
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt'
        )
    
    def handle(self, *args, **options):
        username = options['username']
        force = options['force']

        current_owner = User.objects.filter(is_owner=True).first()
        
        if not current_owner:
            self.stdout.write(self.style.WARNING('No owner exists!'))
            confirm = input('Create owner from this user? (y/n): ')
            if confirm.lower() == 'y':
                self._create_owner(username, force)
            else:
                self.stdout.write('Operation canceled')
            return
        
        try:
            new_owner = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" not found'))
            return
        
        if new_owner == current_owner:
            self.stdout.write(self.style.ERROR(f'User "{username}" is already the owner'))
            return
        
        if not new_owner.is_superuser or not new_owner.is_staff:
            self.stdout.write(
                self.style.ERROR('The new owner must be a superadmin and staff')
            )
            return
        
        if not force:
            self.stdout.write(f'Current owner: {current_owner.username}')
            confirm = input(f'Transfer ownership to "{username}"? (y/n): ')
            
            if confirm.lower() != 'y':
                self.stdout.write('Operation canceled')
                return
        
        current_owner.is_owner = False
        current_owner.save()
        
        new_owner.is_owner = True
        new_owner.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'Owner rights transferred to "{username}"')
        )
        self.stdout.write(
            f'   Previous owner: {current_owner.username} (rights revoked)'
        )
    
    def _create_owner(self, username, force):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" not found'))
            return
        
        if not user.is_superuser or not user.is_staff:
            self.stdout.write(
                self.style.ERROR('User must be a superadmin and staff to become owner')
            )
            return
        
        if not force:
            confirm = input(f'Make "{username}" the owner? (y/n): ')
            if confirm.lower() != 'y':
                self.stdout.write('Operation canceled')
                return
        
        user.is_owner = True
        user.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'User "{username}" is now the owner')
        )