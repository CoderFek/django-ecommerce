import csv
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from products.models import Product


class Command(BaseCommand):
    help = (
        "Import products from CSV into Product model.\n"
        "Required CSV columns: country, description, price, province, title, variety, winery\n"
        "Optional CSV columns: image_url (or image), stock\n"
        "Use --update to update existing products found by title+winery."
    )

    def add_arguments(self, parser):
        # Positional argument: path to csv file
        parser.add_argument("csv_file", type=str, help="Path to your CSV file")
        # Optional flag to update existing products
        parser.add_argument(
            "--update",
            action="store_true",
            help="If provided, update existing products (matched by title+winery)",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        update_existing = options["update"]

        # Try opening the CSV; raise a clean error if not found
        try:
            f = open(csv_file, newline="", encoding="utf-8")
        except FileNotFoundError:
            raise CommandError(f"CSV file not found: {csv_file}")

        reader = csv.DictReader(f)

        # Ensure required columns are present
        required = ["country", "description", "price", "province", "title", "variety", "winery"]
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            f.close()
            raise CommandError(f"CSV is missing required columns: {', '.join(missing)}")

        created = 0
        updated = 0
        skipped = 0
        errors = 0

        # Iterate rows with an index for helpful messages
        for i, row in enumerate(reader, start=1):
            # Keep each row inside a transaction so partial failures don't corrupt DB
            with transaction.atomic():
                try:
                    # Read and normalize required fields
                    title = (row.get("title") or "").strip()
                    winery = (row.get("winery") or "").strip()
                    if not title or not winery:
                        self.stdout.write(self.style.WARNING(f"Row {i}: missing title or winery → skipped"))
                        skipped += 1
                        continue

                    # Parse price into Decimal (safe for DecimalField)
                    price_raw = (row.get("price") or "").strip()
                    try:
                        price = Decimal(price_raw) if price_raw != "" else Decimal("0.00")
                    except InvalidOperation:
                        self.stdout.write(self.style.WARNING(f"Row {i}: invalid price '{price_raw}' → set to 0.00"))
                        price = Decimal("0.00")

                    # Prepare defaults dict for product creation/update
                    defaults = {
                        "description": (row.get("description") or "").strip(),
                        "price": price,
                        "country_of_origin": (row.get("country") or "").strip(),
                        "province": (row.get("province") or "").strip(),
                        "variety": (row.get("variety") or "").strip(),
                        "winery": winery,
                    }

                    # image_url may be named 'image_url' or 'image' in CSV; default to empty string
                    image_url = row.get("image_url") or row.get("image") or ""
                    defaults["image_url"] = image_url.strip() if image_url else ""

                    # If CSV contains stock, try to parse it; otherwise leave out so model default (200) applies
                    stock_raw = row.get("stock")
                    if stock_raw:
                        try:
                            defaults["stock"] = int(stock_raw)
                        except ValueError:
                            self.stdout.write(self.style.WARNING(f"Row {i}: invalid stock '{stock_raw}' → using model default"))

                    # Try to find existing product by title + winery
                    product_qs = Product.objects.filter(title=title, winery=winery)
                    product = product_qs.first()

                    if product:
                        if update_existing:
                            # Update only if values changed (minimize writes)
                            changed = False
                            for field, val in defaults.items():
                                current = getattr(product, field, None)
                                # For decimals and ints the direct comparison works; for strings guard against None
                                if (current is None and val) or (current != val):
                                    setattr(product, field, val)
                                    changed = True
                            if changed:
                                product.save()
                                updated += 1
                                self.stdout.write(self.style.SUCCESS(f"Row {i}: Updated {product.title}"))
                            else:
                                skipped += 1
                                self.stdout.write(f"Row {i}: No changes for {product.title} → skipped")
                        else:
                            skipped += 1
                            self.stdout.write(f"Row {i}: {product.title} already exists → skipped (use --update to overwrite)")
                    else:
                        # Create new product with defaults; stock will default to model default if not in defaults
                        product = Product.objects.create(title=title, **defaults)
                        created += 1
                        self.stdout.write(self.style.SUCCESS(f"Row {i}: Created {product.title}"))

                except Exception as exc:
                    errors += 1
                    self.stdout.write(self.style.ERROR(f"Row {i}: Error importing row → {exc}"))

        f.close()

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f"Import complete: created={created} updated={updated} skipped={skipped} errors={errors}"
        ))
