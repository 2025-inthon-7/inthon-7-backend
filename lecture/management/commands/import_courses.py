import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from lecture.models import Course


class Command(BaseCommand):
    help = "Import or update Course rows from courses.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default=None,
            help="Path to courses.csv (default: BASE_DIR/courses.csv)",
        )

    def handle(self, *args, **options):
        path = options["path"] or os.path.join(settings.BASE_DIR, "courses.csv")

        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        created_count = 0
        updated_count = 0

        # 한글 헤더/내용 고려해서 utf-8-sig 사용
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row["code"].strip()
                name = row["name"].strip()
                professor = row["professor"].strip()
                time = row["time"].strip()

                obj, created = Course.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": name,
                        "professor": professor,
                        "time": time,
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. created={created_count}, updated={updated_count}"
            )
        )


