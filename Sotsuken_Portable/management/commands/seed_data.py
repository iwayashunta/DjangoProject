import random
from django.core.management.base import BaseCommand
from faker import Faker
from Sotsuken_Portable.models import User, Group, GroupMember, SafetyStatus, SupportRequest


class Command(BaseCommand):
    help = 'Generates dummy data for the application'

    def handle(self, *args, **kwargs):
        # 乱数シードを固定する
        # この値を同じにしておけば、誰が実行しても同じデータが生成される
        SEED_VALUE = 1234
        random.seed(SEED_VALUE)
        Faker.seed(SEED_VALUE)
        # 0. 実行前の確認
        self.stdout.write(
            self.style.WARNING('This command will delete all existing data. Do you want to continue? (yes/no)'))
        confirmation = input()
        if confirmation.lower() != 'yes':
            self.stdout.write(self.style.ERROR('Operation cancelled.'))
            return

        # 1. 既存のデータを削除
        self.stdout.write('Deleting old data...')
        # 依存関係を考慮して、関連モデルから削除
        GroupMember.objects.all().delete()
        SupportRequest.objects.all().delete()
        SafetyStatus.objects.all().delete()
        Group.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()  # スーパーユーザーは削除しない

        # Fakerインスタンスを作成（日本語のデータを生成）
        faker = Faker('ja_JP')

        # 2. ユーザーを生成 (例: 50人)
        self.stdout.write('Creating new users...')
        users = []
        for _ in range(50):
            full_name = faker.name()
            email = faker.email()
            user = User.objects.create_user(
                email=email,
                password='password123',  # 全員同じパスワードで作成
                full_name=full_name,
                username=email.split('@')[0]  # usernameにも仮の値を入れておく
            )
            users.append(user)
        self.stdout.write(self.style.SUCCESS(f'{len(users)} users created.'))

        # 3. グループを生成 (例: 5つ)
        self.stdout.write('Creating groups...')
        groups = []
        for _ in range(5):
            group_name = f"{faker.word()}の会"
            creator = random.choice(users)
            group = Group.objects.create(name=group_name, creator=creator)
            groups.append(group)
        self.stdout.write(self.style.SUCCESS(f'{len(groups)} groups created.'))

        # 4. ユーザーをグループに参加させる
        self.stdout.write('Adding users to groups...')
        for user in users:
            # 各ユーザーを1つか2つのグループにランダムで参加させる
            num_groups = random.randint(1, 2)
            groups_to_join = random.sample(groups, num_groups)
            for group in groups_to_join:
                GroupMember.objects.create(group=group, member=user)
        self.stdout.write(self.style.SUCCESS('Users added to groups.'))

        # 5. 各ユーザーの安否状況を生成
        self.stdout.write('Creating safety statuses...')
        for user in users:
            SafetyStatus.objects.create(
                user=user,
                status=random.choice(['safe', 'help', 'unknown']),
                message=faker.sentence()
            )
        self.stdout.write(self.style.SUCCESS('Safety statuses created.'))

        # 6. 支援要請を生成 (例: 15件)
        self.stdout.write('Creating support requests...')
        for _ in range(15):
            SupportRequest.objects.create(
                requester=random.choice(users),
                category=random.choice([c[0] for c in SupportRequest.CATEGORY_CHOICES]),
                priority=random.choice([p[0] for p in SupportRequest.PRIORITY_CHOICES]),
                details=faker.text(max_nb_chars=100)
            )
        self.stdout.write(self.style.SUCCESS('Support requests created.'))

        self.stdout.write(self.style.SUCCESS('Dummy data generation complete!'))