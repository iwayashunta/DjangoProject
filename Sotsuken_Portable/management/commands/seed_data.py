import random
from django.core.management.base import BaseCommand
from faker import Faker
# ↓ usernameを使うようにモデルをインポート
from Sotsuken_Portable.models import User, Group, GroupMember


# ↓ 不要なモデルのインポートはコメントアウト
# from Sotsuken_Portable.models import SafetyStatus, SupportRequest, Message

class Command(BaseCommand):
    help = 'Generates dummy data for users and groups'

    def handle(self, *args, **kwargs):
        # 乱数シードを固定
        SEED_VALUE = 1234
        random.seed(SEED_VALUE)
        Faker.seed(SEED_VALUE)

        # 実行前の確認
        self.stdout.write(self.style.WARNING('This will delete existing user and group data. Continue? (yes/no)'))
        if input().lower() != 'yes':
            self.stdout.write(self.style.ERROR('Operation cancelled.'))
            return

        # 1. 既存のデータを削除 (削除対象を絞る)
        self.stdout.write('Deleting old data...')
        GroupMember.objects.all().delete()
        # SupportRequest.objects.all().delete() # コメントアウト
        # SafetyStatus.objects.all().delete()   # コメントアウト
        # Message.objects.all().delete()        # コメントアウト
        Group.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()

        faker = Faker('ja_JP')

        # 2. ユーザーを生成 (username を使うように修正)
        self.stdout.write('Creating new users...')
        users = []
        for i in range(50):
            # usernameを生成 (例: user001, user002, ...)
            username = f'user{i + 1:03}'
            full_name = faker.name()
            email = faker.unique.email()  # faker.email()だと重複する可能性があるので unique.email() を使う

            user = User.objects.create_user(
                username=username,  # username を指定
                password='password123',
                full_name=full_name,
                email=email,
                # username にも仮の値を入れておく
                username=username
            )
            users.append(user)
        self.stdout.write(self.style.SUCCESS(f'{len(users)} users created.'))

        # 3. グループを生成
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
            num_groups = random.randint(1, 2)
            groups_to_join = random.sample(groups, num_groups)
            for group in groups_to_join:
                GroupMember.objects.create(group=group, member=user)
        self.stdout.write(self.style.SUCCESS('Users added to groups.'))

        # --- 以下のデータ生成は一旦コメントアウト ---
        # # 5. 各ユーザーの安否状況を生成
        # self.stdout.write('Creating safety statuses...')
        # for user in users:
        #     SafetyStatus.objects.create(...)
        # self.stdout.write(self.style.SUCCESS('Safety statuses created.'))

        # # 6. 支援要請を生成
        # self.stdout.write('Creating support requests...')
        # for _ in range(15):
        #     SupportRequest.objects.create(...)
        # self.stdout.write(self.style.SUCCESS('Support requests created.'))

        # # 7. チャットメッセージを生成
        # self.stdout.write('Creating chat messages...')
        # for _ in range(200):
        #     Message.objects.create(...)
        # self.stdout.write(self.style.SUCCESS('Chat messages created.'))
        # --- ここまで ---

        self.stdout.write(self.style.SUCCESS('Dummy data generation for users and groups is complete!'))