import csv
import re
from django.core.management.base import BaseCommand, CommandError
from stock.models import DefaultCropRecipe, DefaultCropRecipeItem


class Command(BaseCommand):
    help = "Import or update DefaultCropRecipe/DefaultCropRecipeItem data from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to the CSV file")
        parser.add_argument(
            "--min-confidence",
            type=str,
            default="estimate_unverified",
            choices=["verified_myanmar", "estimate_unverified", "no_data"],
            help=(
                "Skip rows below this confidence level. Order (strictest first): "
                "verified_myanmar > estimate_unverified > no_data. "
                "Default 'estimate_unverified' imports verified + estimated rows, skips 'no_data' rows."
            ),
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete all existing DefaultCropRecipeItem rows for crop types found in the CSV before importing.",
        )

    def parse_application_time(self, app_time):
        """Parse application time string to days after planting."""
        if not app_time:
            return 0

        app_time = app_time.lower().strip()

        if "before planting" in app_time:
            return -7

        if "planting day" in app_time or "planting season" in app_time:
            return 0

        match = re.search(r'(\d+)\s*(?:days?|day)\s*(?:after|before)?\s*planting', app_time)
        if match:
            days = int(match.group(1))
            if "before" in app_time:
                return -days
            return days

        if "weekly" in app_time:
            return 7
        if "fruit" in app_time or "flowering" in app_time:
            return 30
        if "early growth" in app_time:
            return 10
        if "growth" in app_time:
            return 14
        if "monthly" in app_time:
            return 30

        return 14

    def map_crop_name_to_type(self, crop_name):
        mapping = {
            "RICE": "RICE",
            "CORN": "CORN",
            "WHEAT": "WHEAT",
            "SOYBEAN": "SOYBEAN",
            "COTTON": "COTTON",
            "TOMATO": "VEGETABLE",
            "MANGO": "FRUIT",
        }
        return mapping.get(crop_name.upper())

    def map_material_type_to_category(self, material_type):
        """Map material_type to model category choices - MUST match Material.CATEGORY_CHOICES exactly (lowercase)."""
        if not material_type:
            return "other"

        mapping = {
            "FERTILIZER": "fertilizer",
            "SEED": "seed",
            "PESTICIDE": "pesticide",
            "SEEDLING": "seed",
            "LABOR": "labor",
        }
        return mapping.get(material_type.upper(), "other")

    def map_unit(self, unit_raw):
        """Normalize CSV unit text to Material.UNIT_CHOICES codes (lowercase)."""
        if not unit_raw:
            return "unit"

        mapping = {
            "kg": "kg",
            "g": "g",
            "gram": "g",
            "litre": "l",
            "liter": "l",
            "l": "l",
            "bag": "bag",
            "packet": "packet",
            "unit": "unit",
            "tree": "tree",
            "person-day": "person_day",
            "person_day": "person_day",
        }
        return mapping.get(unit_raw.strip().lower(), "unit")

    def normalize_quantity(self, quantity_float, unit):
        """
        Prevents sub-1 quantities (e.g. 0.2 kg) from truncating to 0 when saved
        into an IntegerField. If saving as-is would round to zero, convert
        kg -> g (x1000) first to preserve real precision.
        """
        if unit == "kg" and 0 < quantity_float < 1:
            return round(quantity_float * 1000), "g"
        return int(round(quantity_float)), unit

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        min_confidence = options["min_confidence"]
        replace = options["replace"]

        confidence_rank = {"verified_myanmar": 0, "estimate_unverified": 1, "no_data": 2}
        min_rank = confidence_rank[min_confidence]

        try:
            f = open(csv_path, newline="", encoding="utf-8")
        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")

        reader = csv.DictReader(f)

        required_cols = {"crop_name", "material_name", "unit", "quantity_per_acre", "application_time", "material_type"}
        fieldnames = set(reader.fieldnames or [])

        if not required_cols.issubset(fieldnames):
            missing = required_cols - fieldnames
            raise CommandError(f"CSV missing required columns: {', '.join(sorted(missing))}")

        rows = list(reader)
        f.close()

        if replace:
            crop_types_in_csv = set()
            for row in rows:
                crop_name = row.get("crop_name", "").strip()
                crop_type = self.map_crop_name_to_type(crop_name)
                if crop_type:
                    crop_types_in_csv.add(crop_type)

            if crop_types_in_csv:
                deleted, _ = DefaultCropRecipeItem.objects.filter(
                    recipe__crop_type__in=crop_types_in_csv
                ).delete()
                self.stdout.write(self.style.WARNING(
                    f"Deleted {deleted} existing recipe items for crop types: {', '.join(sorted(crop_types_in_csv))}"
                ))

        imported = 0
        skipped_confidence = 0
        skipped_error = 0
        skipped_unknown_crop = 0
        skipped_zero_quantity = 0
        skipped_no_material_type = 0

        for row in rows:
            confidence = row.get("confidence", "estimate_unverified").strip()
            row_rank = confidence_rank.get(confidence, 1)

            if row_rank > min_rank:
                skipped_confidence += 1
                continue

            crop_name = row.get("crop_name", "").strip()
            material_name = row.get("material_name", "").strip()
            material_type = row.get("material_type", "").strip()
            application_time = row.get("application_time", "").strip()
            purpose = row.get("purpose", "").strip()
            cost_per_unit_raw = row.get("cost_per_unit", "").strip()
            unit_raw = row.get("unit", "").strip()

            if not crop_name or not material_name:
                self.stdout.write(self.style.WARNING("Skipping row with missing crop_name or material_name"))
                skipped_error += 1
                continue

            if not material_type:
                self.stdout.write(self.style.WARNING(
                    f"Skipping row with missing material_type: {crop_name} / {material_name}"
                ))
                skipped_no_material_type += 1
                continue

            try:
                quantity_float = float(row.get("quantity_per_acre", 0))
                if quantity_float <= 0:
                    self.stdout.write(self.style.WARNING(
                        f"Skipping row with zero/negative quantity: {crop_name} / {material_name}"
                    ))
                    skipped_zero_quantity += 1
                    continue
            except (ValueError, TypeError):
                self.stdout.write(self.style.ERROR(
                    f"Skipping row with invalid quantity: {crop_name} / {material_name} "
                    f"(value: {row.get('quantity_per_acre', 'N/A')})"
                ))
                skipped_error += 1
                continue

            crop_type = self.map_crop_name_to_type(crop_name)
            if not crop_type:
                self.stdout.write(self.style.WARNING(
                    f"Skipping unknown crop_name '{crop_name}' for material '{material_name}'"
                ))
                skipped_unknown_crop += 1
                continue

            category = self.map_material_type_to_category(material_type)
            unit = self.map_unit(unit_raw)

            # Convert to int, upgrading kg->g if needed to avoid truncating small quantities to 0
            quantity, unit = self.normalize_quantity(quantity_float, unit)
            if quantity == 0:
                self.stdout.write(self.style.WARNING(
                    f"Quantity rounded to 0 for {crop_name} / {material_name} "
                    f"(original: {quantity_float} {unit_raw}) - skipping row"
                ))
                skipped_zero_quantity += 1
                continue

            try:
                default_unit_cost = int(round(float(cost_per_unit_raw))) if cost_per_unit_raw else 0
            except ValueError:
                default_unit_cost = 0

            days = self.parse_application_time(application_time)

            valid_crop_types = dict(DefaultCropRecipe._meta.get_field("crop_type").choices)
            if crop_type not in valid_crop_types:
                self.stdout.write(self.style.ERROR(
                    f"Skipping invalid crop_type '{crop_type}' for material '{material_name}'"
                ))
                skipped_error += 1
                continue

            recipe, created = DefaultCropRecipe.objects.get_or_create(crop_type=crop_type)
            if created:
                self.stdout.write(f"Created new recipe for crop type: {crop_type}")

            notes_parts = []
            if purpose:
                notes_parts.append(f"Purpose: {purpose}")
            if application_time:
                notes_parts.append(f"Application: {application_time}")
            growth_stage = row.get("growth_stage", "").strip()
            if growth_stage:
                notes_parts.append(f"Growth stage: {growth_stage}")
            notes = " | ".join(notes_parts) if notes_parts else ""

            try:
                item, created = DefaultCropRecipeItem.objects.update_or_create(
                    recipe=recipe,
                    material_name=material_name,
                    days_after_planting=days,
                    defaults={
                        "category": category,
                        "unit": unit,
                        "quantity_per_acre": quantity,
                        "default_unit_cost": default_unit_cost,
                        "notes": notes,
                    },
                )
                imported += 1
                action = "Created" if created else "Updated"
                self.stdout.write(f"  \u2713 {action}: {material_name} ({category}) for {crop_type} (Day {days})")
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"  \u2717 Error saving {material_name} for {crop_type}: {str(e)}"
                ))
                skipped_error += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n{'=' * 50}\n"
            f"IMPORT COMPLETE\n"
            f"{'=' * 50}\n"
            f"\u2713 Imported/updated: {imported} recipe items\n"
            f"\u2717 Skipped below confidence threshold: {skipped_confidence}\n"
            f"\u2717 Skipped unknown crop names: {skipped_unknown_crop}\n"
            f"\u2717 Skipped zero quantity: {skipped_zero_quantity}\n"
            f"\u2717 Skipped missing material_type: {skipped_no_material_type}\n"
            f"\u2717 Skipped other errors: {skipped_error}\n"
            f"{'=' * 50}"
        ))