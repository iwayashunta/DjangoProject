import csv
import os
import random
from django.conf import settings
from django.core.management.base import BaseCommand
from Sotsuken_Portable.models import Shelter

class Command(BaseCommand):
    help = 'Seeds the database with shelter data from a CSV file.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding shelter data from CSV...')

        # プロジェクトのルートディレクトリにある 'shelters.csv' のパスを構築
        csv_file_path = os.path.join(settings.BASE_DIR, 'shelters.csv')

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
                # DictReaderを使うと、各行を辞書として扱える
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    # CSVから読み込んだ値の型を変換
                    try:
                        latitude = float(row['latitude'])
                        longitude = float(row['longitude'])
                        max_capacity = int(row['max_capacity'])
                        # 'true', '1', 'yes' などをTrueに変換
                        is_pet_friendly = row['is_pet_friendly'].lower() in ['true', '1', 'yes']
                    except (ValueError, KeyError) as e:
                        self.stdout.write(self.style.ERROR(f"Skipping row due to data error in '{row.get('name', 'N/A')}': {e}"))
                        continue

                    # update_or_createでデータの作成・更新
                    shelter, created = Shelter.objects.update_or_create(
                        management_id=row['management_id'],
                        defaults={
                            'name': row['name'],
                            'address': row['address'],
                            'latitude': latitude,
                            'longitude': longitude,
                            'max_capacity': max_capacity,
                            'current_occupancy': random.randint(0, max_capacity // 4),
                            'opening_status': 'open',
                            'is_pet_friendly': is_pet_friendly,
                        }
                    )

                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Successfully created shelter: "{shelter.name}"'))
                    else:
                        self.stdout.write(self.style.WARNING(f'Shelter "{shelter.name}" already existed, updated.'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"CSV file not found at: {csv_file_path}"))
            return

        self.stdout.write(self.style.SUCCESS('Shelter seeding from CSV complete.'))
