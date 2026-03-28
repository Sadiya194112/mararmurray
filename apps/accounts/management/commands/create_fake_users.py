from django.core.management.base import BaseCommand

from apps.accounts.models import User

FAKE_USERS = [
    {"full_name": "Alice Johnson", "email": "alice@test.com", "role": "student"},
    {"full_name": "Bob Smith", "email": "bob@test.com", "role": "student"},
    {"full_name": "Carol White", "email": "carol@test.com", "role": "student"},
    {"full_name": "David Brown", "email": "david@test.com", "role": "university"},
    {"full_name": "Eve Davis", "email": "eve@test.com", "role": "university"},
]

DEFAULT_PASSWORD = "Test@1234"


class Command(BaseCommand):
    help = "Create fake users for testing disable/delete API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            type=str,
            default=DEFAULT_PASSWORD,
            help=f"Password for all fake users (default: {DEFAULT_PASSWORD})",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing fake test users before creating new ones",
        )

    def handle(self, *args, **options):
        password = options["password"]

        if options["clear"]:
            test_emails = [u["email"] for u in FAKE_USERS]
            deleted_count, _ = User.objects.filter(email__in=test_emails).delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {deleted_count} existing fake user(s).")
            )

        created = 0
        skipped = 0

        for user_data in FAKE_USERS:
            email = user_data["email"]
            if User.objects.filter(email=email).exists():
                self.stdout.write(
                    self.style.WARNING(f"  SKIP  {email} (already exists)")
                )
                skipped += 1
                continue

            User.objects.create_user(
                full_name=user_data["full_name"],
                email=email,
                password=password,
                role=user_data["role"],
                is_active=True,
                terms_and_conditions=True,
            )
            self.stdout.write(
                self.style.SUCCESS(f"  OK    {email}  [{user_data['role']}]")
            )
            created += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created}  |  Skipped: {skipped}  |  Password: {password}"
            )
        )
