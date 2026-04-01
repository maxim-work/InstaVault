from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import getpass

User = get_user_model()


class Command(BaseCommand):
    help = 'Create owner (main superadmin)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username for the owner'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email for the owner'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for the owner (not secure, use with caution)'
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Run in non-interactive mode (requires --username and --password)'
        )
    
    def handle(self, *args, **options):
        if User.objects.filter(is_owner=True).exists():
            self.stdout.write(self.style.ERROR('Owner already exists!'))
            return
        
        if options['no_input']:
            self._create_non_interactive(options)
            return
        
        self._create_interactive()
    
    def _create_non_interactive(self, options):
        username = options.get('username')
        password = options.get('password')
        email = options.get('email', '')
        
        if not username or not password:
            self.stdout.write(
                self.style.ERROR('Username and password are required in non-interactive mode')
            )
            return
        
        try:
            self._create_owner(username, email, password)
            self.stdout.write(
                self.style.SUCCESS(f'Owner created successfully: {username}')
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
    
    def _create_interactive(self):
        self.stdout.write("\nCreate OWNER (main superadmin)\n")
        
        try:
            while True:
                username = input("Username: ").strip()
                if not username:
                    self.stdout.write(self.style.ERROR("Username is required!"))
                    continue
                
                if User.objects.filter(username=username).exists():
                    self.stdout.write(
                        self.style.ERROR(f"User '{username}' already exists!")
                    )
                    continue
                break
            
            email = input("Email (optional): ").strip()
            if email:
                try:
                    validate_email(email)
                except ValidationError:
                    self.stdout.write(self.style.WARNING("Invalid email format. Skipping..."))
                    email = ''
            
            while True:
                password = getpass.getpass("Password: ")
                password2 = getpass.getpass("Confirm password: ")
                
                if not password:
                    self.stdout.write(self.style.ERROR("Password is required!"))
                    continue
                
                if password != password2:
                    self.stdout.write(self.style.ERROR("Passwords don't match!"))
                    continue
                
                if len(password) < 4:
                    self.stdout.write(self.style.ERROR("Password must be at least 4 characters!"))
                    continue
                
                break
            
            self._create_owner(username, email, password)
            
            self.stdout.write(self.style.SUCCESS(f"\nOwner created: {username}"))
            self.stdout.write(self.style.WARNING("\nSave your password in a safe place!"))
            
        except KeyboardInterrupt:
            self.stdout.write("\n\nСreation cancelled")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nError: {e}"))
    
    def _create_owner(self, username, email, password):
        owner = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        owner.is_owner = True
        owner.save()