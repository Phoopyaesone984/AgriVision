import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal, InvalidOperation
from marketPrice.models import Crop, HarvestPrice, YieldData, Profitability
import os
import re


TON_TO_VISS = Decimal("612.4")

# Pounds per basket from the CSO yield table.
BASKET_LB = {
    "46lb(basket)": Decimal("46"),
    "55lb(basket)": Decimal("55"),
    "69lb(basket)": Decimal("69"),
    "72lb(basket)": Decimal("72"),
}

LB_PER_TON = Decimal("2204.62262185")

# =========================================================
# REALISTIC PRODUCTION COSTS PER ACRE (Kyat)
# =========================================================
PRODUCTION_COSTS = {
    'rice': Decimal("800000"),
    'onion': Decimal("1200000"),
    'potato': Decimal("1500000"),
    'garlic': Decimal("2000000"),
    'pulse': Decimal("600000"),
    'bean': Decimal("600000"),
    'coffee': Decimal("2500000"),
    'tea': Decimal("1800000"),
    'chillies': Decimal("2200000"),
    'tobacco': Decimal("3000000"),
    'sugarcane': Decimal("1000000"),
    'tapioca': Decimal("900000"),
    'groundnut': Decimal("1200000"),
    'sesamum': Decimal("800000"),
    'cotton': Decimal("1500000"),
}
DEFAULT_COST = Decimal("1500000")


def clean_year(value):
    """Normalize 2019_2020 / 2019-2020 / 2019-20 to 2019-20."""
    if pd.isna(value):
        return None
    s = str(value).strip().replace("_", "-").replace("/", "-")
    nums = re.findall(r"\d{2,4}", s)
    if len(nums) >= 2:
        start = nums[0]
        end = nums[1]
        if len(start) == 4:
            end = end[-2:]
            return f"{start}-{end}"
    return s


def clean_crop_name(value):
    """Remove CSO row numbering and normalize spacing."""
    if pd.isna(value):
        return ""
    s = str(value).strip()
    s = re.sub(r"^\s*\d+\.\s*", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def decimal_or_none(value):
    if pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def get_production_cost(crop_name):
    """Get realistic production cost per acre for a crop"""
    crop_name_lower = crop_name.lower()
    for key, cost in PRODUCTION_COSTS.items():
        if key in crop_name_lower:
            return cost
    return DEFAULT_COST


class Command(BaseCommand):
    help = (
        "Rebuild Profitability from CSO harvest-price and yield data. "
        "FIXED: Now stores REAL profit (gross revenue minus production costs) "
        "in the profit_per_acre field."
    )

    def handle(self, *args, **options):
        data_dir = os.path.join(os.getcwd(), "data")
        price_file = os.path.join(data_dir, "crop_prices_2019_2025.csv")
        yield_file = os.path.join(
            data_dir, "table_3_04_average_yield_per_harvested_acre.csv"
        )

        if not os.path.exists(price_file):
            self.stdout.write(self.style.ERROR(f"Price file not found: {price_file}"))
            return

        if not os.path.exists(yield_file):
            self.stdout.write(self.style.ERROR(f"Yield file not found: {yield_file}"))
            return

        self.stdout.write(self.style.SUCCESS("Starting CORRECTED profitability import..."))
        self.stdout.write(f"1 metric ton = {TON_TO_VISS} viss")
        self.stdout.write("")

        with transaction.atomic():
            # ------------------------------------------------------------
            # 1. Read harvest prices
            # ------------------------------------------------------------
            df_prices = pd.read_csv(price_file)
            df_prices.columns = df_prices.columns.str.strip()

            price_records = {}
            for _, row in df_prices.iterrows():
                crop_name = clean_crop_name(row.get("crop_name"))
                unit = str(row.get("unit", "")).strip()

                if not crop_name:
                    continue

                crop = self._find_or_create_crop(crop_name, unit)

                for column in df_prices.columns:
                    if not column.startswith("price_"):
                        continue

                    value = decimal_or_none(row[column])
                    if value is None:
                        continue

                    year = clean_year(column.replace("price_", ""))
                    if not year:
                        continue

                    HarvestPrice.objects.update_or_create(
                        crop=crop,
                        year=year,
                        defaults={"price": value},
                    )

                    price_records[(self._key(crop_name), year)] = {
                        "crop": crop,
                        "price": value,
                        "unit": unit,
                    }

            self.stdout.write(f"Loaded {len(price_records)} price records")

            # ------------------------------------------------------------
            # 2. Read CSO yield data
            # ------------------------------------------------------------
            df_yields = pd.read_csv(yield_file)
            df_yields.columns = df_yields.columns.str.strip()

            yield_records = {}

            for _, row in df_yields.iterrows():
                raw_name = row.get("sn_crop")
                crop_name = clean_crop_name(raw_name)
                source_unit = str(row.get("unit", "")).strip()

                if not crop_name:
                    continue

                crop = self._find_or_create_crop(crop_name, source_unit)

                for column in df_yields.columns:
                    if column == "sn_crop" or column == "unit":
                        continue

                    year = clean_year(column)
                    if not year:
                        continue

                    value = decimal_or_none(row[column])
                    if value is None:
                        continue

                    YieldData.objects.update_or_create(
                        crop=crop,
                        year=year,
                        defaults={
                            "yield_value": value,
                            "unit": source_unit,
                        },
                    )

                    yield_records[(self._key(crop_name), year)] = {
                        "crop": crop,
                        "yield_value": value,
                        "unit": source_unit,
                    }

            self.stdout.write(f"Loaded {len(yield_records)} yield records")
            self.stdout.write("")

            # ------------------------------------------------------------
            # 3. Rebuild profitability with CORRECT calculations
            # ------------------------------------------------------------
            Profitability.objects.all().delete()

            created = 0
            skipped = 0
            corrupted_yield = 0
            revenue_log = []

            for (price_key, year), price_info in price_records.items():
                # Find matching yield by normalized crop key + year.
                yield_info = yield_records.get((price_key, year))

                # Try aliases where CSO names differ slightly.
                if yield_info is None:
                    yield_info = self._find_yield_alias(
                        price_key, year, yield_records
                    )

                if yield_info is None:
                    skipped += 1
                    continue

                # =========================================================
                # CRITICAL: Convert yield to tons/acre
                # =========================================================
                yield_tons = self._yield_to_tons(
                    yield_info["yield_value"], yield_info["unit"]
                )

                if yield_tons is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠ Cannot convert yield for {price_info['crop'].name} "
                            f"{year}: {yield_info['unit']}"
                        )
                    )
                    corrupted_yield += 1
                    continue

                # =========================================================
                # Check for impossibly high yield (data corruption)
                # =========================================================
                if yield_tons > Decimal("100"):
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠ IMPOSSIBLE YIELD for {price_info['crop'].name} "
                            f"{year}: {yield_tons:.1f} tons/acre - likely wrong unit!"
                        )
                    )
                    corrupted_yield += 1
                    continue

                # =========================================================
                # Calculate GROSS REVENUE per acre
                # =========================================================
                price_per_ton = self._price_to_ton(
                    price_info["price"], price_info["unit"]
                )

                if price_per_ton is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠ Cannot convert price for {price_info['crop'].name} "
                            f"{year}: {price_info['unit']}"
                        )
                    )
                    corrupted_yield += 1
                    continue

                revenue_per_acre = price_per_ton * yield_tons

                # =========================================================
                # NEW: Calculate REAL profit (Revenue - Production Costs)
                # =========================================================
                production_cost = get_production_cost(price_info["crop"].name)
                real_profit = revenue_per_acre - production_cost

                # Log the calculation for verification
                revenue_log.append({
                    'crop': price_info["crop"].name,
                    'year': year,
                    'price_per_ton': int(price_per_ton),
                    'yield_tons': float(yield_tons),
                    'revenue': int(revenue_per_acre),
                    'cost': int(production_cost),
                    'profit': int(real_profit),
                    'roi': float((real_profit / production_cost) * 100) if production_cost > 0 else 0,
                })

                # =========================================================
                # Store the REAL profit in the database
                # =========================================================
                Profitability.objects.create(
                    crop=price_info["crop"],
                    year=year,
                    price_per_ton=price_per_ton,
                    yield_tons_per_acre=yield_tons,
                    profit_per_acre=real_profit,  # ← NOW STORING REAL PROFIT!
                )
                created += 1

            # =========================================================
            # Display results summary
            # =========================================================
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(self.style.SUCCESS("IMPORT SUMMARY"))
            self.stdout.write(self.style.SUCCESS("=" * 60))

            self.stdout.write(f"Created: {created} profitability records")
            self.stdout.write(f"Skipped: {skipped} (no matching yield data)")
            self.stdout.write(f"Corrupted yield: {corrupted_yield} (unit conversion issues)")
            self.stdout.write("")

            # Display sample calculations
            self.stdout.write(self.style.SUCCESS("SAMPLE CALCULATIONS:"))
            self.stdout.write("-" * 60)

            # Show top 10 most profitable crops
            revenue_log_sorted = sorted(revenue_log, key=lambda x: x['profit'], reverse=True)

            self.stdout.write(
                f"{'Crop':<20} {'Year':<10} {'Yield':<10} {'Revenue':<15} {'Cost':<15} {'Profit':<15} {'ROI':<10}"
            )
            self.stdout.write("-" * 100)

            for item in revenue_log_sorted[:10]:
                self.stdout.write(
                    f"{item['crop'][:20]:<20} "
                    f"{item['year']:<10} "
                    f"{item['yield_tons']:<10.1f} "
                    f"{item['revenue']:>14,} "
                    f"{item['cost']:>14,} "
                    f"{item['profit']:>14,} "
                    f"{item['roi']:>9.1f}%"
                )

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("✅ Import complete!"))
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "⚠ The old profit_per_acre values were incorrect (gross revenue). "
                "They have been replaced with REAL profit values."
            ))

    # ------------------------------------------------------------------
    # Crop matching
    # ------------------------------------------------------------------
    def _key(self, name):
        s = clean_crop_name(name).lower()
        s = s.replace(" ", "")
        s = s.replace("-", "")
        s = s.replace("_", "")
        s = s.replace("(", "").replace(")", "")
        return s

    def _aliases(self, name):
        key = self._key(name)

        aliases = {
            "paddy": ["paddysummer", "paddymonsoon", "paddy"],
            "chillies": ["chilliesdry", "chilliesgreen", "chillies"],
            "chilli": ["chilliesdry", "chilliesgreen", "chillies"],
            "tea": ["teagreen", "tea"],
            "tobacco": ["tobaccodryvirginia", "tobaccodrymyanmar", "tobacco"],
            "groundnut": ["groundnutrain", "groundnutwinter", "groundnut"],
            "sesamum": ["sesamumearly", "sesamumlate", "sesamum"],
            "cotton": ["cottonwagyi", "cottonmahlaing56", "cottonlongstaple", "cotton"],
        }

        return [key] + aliases.get(key, [])

    def _find_or_create_crop(self, name, unit):
        # Exact first.
        crop = Crop.objects.filter(name__iexact=name).first()
        if crop:
            return crop

        # Conservative normalization matching.
        key = self._key(name)
        for existing in Crop.objects.all():
            if self._key(existing.name) == key:
                return existing

        return Crop.objects.create(
            name=name,
            unit=unit,
        )

    def _find_yield_alias(self, price_key, year, records):
        for key, info in records.items():
            if key[1] != year:
                continue

            yield_key = key[0]
            if price_key == yield_key:
                return info

        return None

    # ------------------------------------------------------------------
    # Unit conversion
    # ------------------------------------------------------------------
    def _price_to_ton(self, price, unit):
        """
        Convert a source price to Ks/metric ton where possible.
        """
        unit_clean = str(unit).strip().lower()

        if unit_clean == "ton":
            return price

        if unit_clean in ("100 basket", "100 baskets"):
            tons = (Decimal("100") * Decimal("46")) / LB_PER_TON
            return price / tons

        return None

    def _yield_to_tons(self, yield_value, unit):
        """
        Convert CSO harvested-acre yield to metric tons/acre.

        CRITICAL FIX: More robust conversion with validation.
        """
        unit_clean = str(unit).strip().lower()

        # If it's already in viss, convert to tons
        if unit_clean == "viss":
            return yield_value / TON_TO_VISS

        # If it's in pounds, convert to tons
        if unit_clean == "lb":
            return yield_value / LB_PER_TON

        # Match basket units
        for basket_unit, pounds in BASKET_LB.items():
            if unit_clean == basket_unit.lower():
                return (yield_value * pounds) / LB_PER_TON

        # If it's in long tons
        if unit_clean == "long ton":
            return yield_value * Decimal("1.0160469088")

        # =========================================================
        # CRITICAL: Check if it might already be in tons
        # =========================================================
        if unit_clean in ("ton", "metric ton", "tons", "metric tons"):
            return yield_value

        return None

    def _calculate_revenue(self, price, price_unit, yield_value, yield_unit):
        """Calculate gross revenue/acre."""
        price_unit_clean = str(price_unit).strip().lower()

        if price_unit_clean == "ton":
            yield_tons = self._yield_to_tons(yield_value, yield_unit)
            if yield_tons is None:
                return None
            return price * yield_tons

        if price_unit_clean in ("100 basket", "100 baskets"):
            yield_unit_clean = str(yield_unit).strip().lower()
            if yield_unit_clean != "46lb(basket)":
                return None
            price_per_basket = price / Decimal("100")
            return price_per_basket * yield_value

        return None