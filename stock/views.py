from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone

from farms.models import Farm, Harvest
from crops.models import Crop

from .forms import (
    StockTransactionForm,
    StockAlertSettingForm,
    MaterialForm,
    MaterialPurchaseForm,
    MaterialUsageForm,
)
from .models import (
    StockAlertSetting,
    StockTransaction,
    Material,
    MaterialPurchase,
    MaterialUsage,
    DefaultCropRecipe,
    DefaultCropRecipeItem,
    CropMaterialPlan,
    CropMaterialPlanItem,
)


@login_required
def stock_list(request):
    harvests = (
        Harvest.objects.filter(crop__farm__owner=request.user)
        .select_related("crop", "crop__farm")
        .prefetch_related("transactions")
    )
    low_stock_harvests = [h for h in harvests if h.is_low_stock]

    return render(request, "stock_list.html", {
        "harvests": harvests,
        "low_stock_count": len(low_stock_harvests),
        "active_tab": "stock",
    })


@login_required
def harvest_stock_detail(request, pk):
    harvest = get_object_or_404(
        Harvest.objects.select_related("crop", "crop__farm"),
        pk=pk, crop__farm__owner=request.user
    )

    if request.method == "POST":
        form = StockTransactionForm(request.POST)
        if form.is_valid():
            txn = form.save(commit=False)
            txn.harvest = harvest
            txn.logged_by = request.user
            txn.save()
            return redirect("stock:harvest_detail", pk=harvest.pk)
    else:
        form = StockTransactionForm()

    setting, _ = StockAlertSetting.objects.get_or_create(harvest=harvest)
    alert_form = StockAlertSettingForm(instance=setting)

    transactions = harvest.transactions.all()

    return render(request, "harvest_stock_detail.html", {
        "harvest": harvest,
        "form": form,
        "alert_form": alert_form,
        "transactions": transactions,
        "active_tab": "stock",
    })


@login_required
@require_POST
def update_alert_setting(request, pk):
    harvest = get_object_or_404(Harvest, pk=pk, crop__farm__owner=request.user)
    setting, _ = StockAlertSetting.objects.get_or_create(harvest=harvest)
    form = StockAlertSettingForm(request.POST, instance=setting)
    if form.is_valid():
        form.save()
    return redirect("stock:harvest_detail", pk=harvest.pk)


@login_required
@require_POST
def delete_transaction(request, pk):
    txn = get_object_or_404(StockTransaction, pk=pk, harvest__crop__farm__owner=request.user)
    harvest_pk = txn.harvest_id
    txn.delete()
    return redirect("stock:harvest_detail", pk=harvest_pk)

@login_required
def material_list(request):
    crops = (
        Crop.objects.filter(farm__owner=request.user)
        .exclude(status="FAILED")
        .select_related("farm")
    )

    return render(request, "material_list.html", {
        "crops": crops,
        "active_tab": "materials",
    })

@login_required
def material_stock(request):
    materials = Material.objects.filter(farm__owner=request.user).select_related("farm")
    low_stock_count = sum(1 for m in materials if m.is_low_stock)

    # Group materials by farm for sectioned display
    farms_map = {}
    for m in materials:
        if m.farm_id not in farms_map:
            farms_map[m.farm_id] = {"farm": m.farm, "materials": []}
        farms_map[m.farm_id]["materials"].append(m)

    farm_groups = sorted(farms_map.values(), key=lambda x: x["farm"].name)

    return render(request, "material_stock.html", {
        "farm_groups": farm_groups,
        "low_stock_count": low_stock_count,
        "materials_count": materials.count(),
        "active_tab": "material_stock",
    })

@login_required
def material_detail(request, pk):
    material = get_object_or_404(Material, pk=pk, farm__owner=request.user)

    purchase_form = MaterialPurchaseForm()
    usage_form = MaterialUsageForm(farm=material.farm)

    if request.method == "POST":
        if "log_purchase" in request.POST:
            purchase_form = MaterialPurchaseForm(request.POST)
            if purchase_form.is_valid():
                p = purchase_form.save(commit=False)
                p.material = material
                p.logged_by = request.user
                p.save()
                return redirect("stock:material_detail", pk=material.pk)
        elif "log_usage" in request.POST:
            usage_form = MaterialUsageForm(request.POST, farm=material.farm)
            if usage_form.is_valid():
                u = usage_form.save(commit=False)
                u.material = material
                u.logged_by = request.user
                u.save()
                return redirect("stock:material_detail", pk=material.pk)

    return render(request, "material_detail.html", {
        "material": material,
        "purchases": material.purchases.all(),
        "usages": material.usages.select_related("crop"),
        "purchase_form": purchase_form,
        "usage_form": usage_form,
        "active_tab": "materials",
    })


@login_required
@require_POST
def delete_material(request, pk):
    material = get_object_or_404(Material, pk=pk, farm__owner=request.user)
    material.delete()
    return redirect("stock:material_list")


@login_required
@require_POST
def delete_purchase(request, pk):
    purchase = get_object_or_404(MaterialPurchase, pk=pk, material__farm__owner=request.user)
    material_pk = purchase.material_id
    purchase.delete()
    return redirect("stock:material_detail", pk=material_pk)


@login_required
@require_POST
def delete_usage(request, pk):
    usage = get_object_or_404(MaterialUsage, pk=pk, material__farm__owner=request.user)
    material_pk = usage.material_id
    usage.delete()
    return redirect("stock:material_detail", pk=material_pk)


# ============================================================
# CROP MATERIAL PLAN — auto-generated from admin's DefaultCropRecipe
# ============================================================

CROP_TIPS = {
    "RICE": "Apply nitrogen fertilizer in split doses to reduce nutrient loss during heavy rain.",
    "CORN": "Side-dress nitrogen once plants reach knee-height for best uptake.",
    "WHEAT": "Apply fungicide before flowering if humidity has been high recently.",
    "SOYBEAN": "Inoculate seeds before planting to boost nitrogen fixation.",
    "COTTON": "Monitor closely for bollworm after the pesticide application window.",
    "VEGETABLE": "Water immediately after fertilizing to help nutrients reach the roots.",
    "FRUIT": "Apply potassium-rich fertilizer as fruit begins to set for better yield.",
    "OTHER": "Follow local agricultural extension guidance for this crop's specific needs.",
}
@login_required
def crop_material_plan(request, pk):
    crop = get_object_or_404(Crop, pk=pk, farm__owner=request.user)
    plan, created = CropMaterialPlan.objects.get_or_create(crop=crop)

    if created:
        default_recipe = DefaultCropRecipe.objects.filter(crop_type=crop.crop_type).first()
        if default_recipe:
            for item in default_recipe.items.all():
                needed_quantity = int(round(item.quantity_per_acre * float(crop.area_acres)))
                material, material_created = Material.objects.get_or_create(
                    farm=crop.farm, name=item.material_name,
                    defaults={
                        "category": item.category,
                        "unit": item.unit,
                        "reorder_threshold": max(1, round(needed_quantity * 0.2)),
                    },
                )
                actual_cost = material.latest_cost_per_unit if material.latest_cost_per_unit > 0 else item.default_unit_cost
                CropMaterialPlanItem.objects.create(
                    plan=plan,
                    material_name=item.material_name,
                    category=item.category,
                    unit=item.unit,
                    quantity=needed_quantity,
                    unit_cost=actual_cost,
                    days_after_planting=item.days_after_planting,
                )

    items = plan.items.all()
    tip = CROP_TIPS.get(crop.crop_type, CROP_TIPS["OTHER"])

    # Real spending breakdown, grouped by material, for this crop
    usage_by_material = {}
    for usage in crop.material_usages.select_related("material"):
        key = usage.material.name
        if key not in usage_by_material:
            usage_by_material[key] = {"quantity": 0, "cost": 0, "unit": usage.material.unit}
        usage_by_material[key]["quantity"] += usage.quantity_used
        usage_by_material[key]["cost"] += usage.total_cost

    actual_total = crop.total_material_cost
    est_total = plan.total_estimated_cost
    variance = actual_total - est_total

    return render(request, "crop_material_plan.html", {
        "crop": crop,
        "plan": plan,
        "items": items,
        "total_cost": est_total,
        "actual_total": actual_total,
        "variance": variance,
        "usage_by_material": usage_by_material,
        "tip": tip,
        "active_tab": "materials",
    })

@login_required
@require_POST
def toggle_item_purchased(request, pk):
    item = get_object_or_404(CropMaterialPlanItem, pk=pk, plan__crop__farm__owner=request.user)
    item.is_purchased = not item.is_purchased
    item.save(update_fields=["is_purchased"])
    return redirect("stock:crop_material_plan", pk=item.plan.crop_id)



@login_required
@require_POST
def toggle_item_applied(request, pk):
    item = get_object_or_404(CropMaterialPlanItem, pk=pk, plan__crop__farm__owner=request.user)

    if item.is_applied:
        # Undo — MaterialUsage ကို ဖျက်ပြီး stock ပြန်ပြင်
        if item.material_usage_id:
            item.material_usage.delete()
        item.is_applied = False
        item.applied_date = None
        item.actual_quantity = None
        item.material_usage = None
        item.save(update_fields=["is_applied", "applied_date", "actual_quantity", "material_usage"])
        return redirect("stock:crop_material_plan", pk=item.plan.crop_id)

    # Mark as Complete — farmer ပြင်ခဲ့တဲ့ actual quantity ကို သုံး၊ မပြင်ရင် planned quantity အတိုင်း
    actual_qty_raw = request.POST.get("actual_quantity")
    try:
        actual_quantity = int(actual_qty_raw) if actual_qty_raw not in (None, "") else item.quantity
    except ValueError:
        actual_quantity = item.quantity
    actual_quantity = max(actual_quantity, 0)

    material, _ = Material.objects.get_or_create(
        farm=item.plan.crop.farm, name=item.material_name,
        defaults={"category": item.category, "unit": item.unit},
    )
    usage = MaterialUsage.objects.create(
        material=material, crop=item.plan.crop, logged_by=request.user,
        quantity_used=actual_quantity, usage_date=timezone.now().date(),
        notes="Auto-logged from material plan schedule",
    )

    item.is_applied = True
    item.applied_date = usage.usage_date
    item.actual_quantity = actual_quantity
    item.material_usage = usage
    item.save(update_fields=["is_applied", "applied_date", "actual_quantity", "material_usage"])

    # ============================================================
    # 🔄 CROP STATUS AUTOMATION LOGIC
    # ============================================================
    crop = item.plan.crop

    if crop.status not in ['HARVESTED', 'FAILED']:
        category = (item.category or '').lower()

        # 1. Seed စိုက်ပျိုးသည့် Task (Day 0 သို့မဟုတ် Category='seed') Complete ဖြစ်လျှင် -> 'PLANTED'
        if category == 'seed' or item.days_after_planting == 0:
            if crop.status == 'PLANNED':
                crop.status = 'PLANTED'
                crop.save(update_fields=['status'])

        elif item.days_after_planting > 0:
            if crop.status in ['PLANNED', 'PLANTED']:
                crop.status = 'GROWING'
                crop.save(update_fields=['status'])


    return redirect("stock:crop_material_plan", pk=item.plan.crop_id)

@login_required
@require_POST
def reschedule_item(request, pk):
    item = get_object_or_404(CropMaterialPlanItem, pk=pk, plan__crop__farm__owner=request.user)
    item.days_after_planting += 7
    item.save(update_fields=["days_after_planting"])
    return redirect("stock:crop_material_plan", pk=item.plan.crop_id)



@login_required
def demand_planning(request):
    upcoming_crops = Crop.objects.filter(
        farm__owner=request.user, status__in=["PLANNED", "PLANTED", "GROWING"]
    ).select_related("farm")

    completed_crops = Crop.objects.filter(
        farm__owner=request.user, status="HARVESTED"
    ).select_related("farm").prefetch_related("material_usages__material")

    # Real historical usage rates, keyed by (crop_type, material_name)
    usage_rates = {}
    for crop in completed_crops:
        if not crop.area_acres:
            continue
        for usage in crop.material_usages.all():
            key = (crop.crop_type, usage.material.name)
            if key not in usage_rates:
                usage_rates[key] = {"qty": 0, "acres": 0, "unit": usage.material.unit, "category": usage.material.category}
            usage_rates[key]["qty"] += usage.quantity_used
            usage_rates[key]["acres"] += float(crop.area_acres)

    # Admin's default recipe rates, keyed by (crop_type, material_name)
    default_rates = {}
    for item in DefaultCropRecipeItem.objects.select_related("recipe"):
        key = (item.recipe.crop_type, item.material_name)
        default_rates[key] = {
            "rate_per_acre": item.quantity_per_acre,
            "unit": item.unit,
            "category": item.category,
        }

    plans = []
    for crop in upcoming_crops:
        farm_materials_by_name = {
            m.name.lower(): m for m in Material.objects.filter(farm=crop.farm)
        }

        # Every material name relevant to this crop type, from either source
        material_names = set()
        for (ct, mname) in usage_rates.keys():
            if ct == crop.crop_type:
                material_names.add(mname)
        for (ct, mname) in default_rates.keys():
            if ct == crop.crop_type:
                material_names.add(mname)

        estimates = []
        for material_name in sorted(material_names):
            key = (crop.crop_type, material_name)
            hist = usage_rates.get(key)
            default = default_rates.get(key)

            if hist and hist["acres"] > 0:
                rate_per_acre = hist["qty"] / hist["acres"]
                estimated_need = round(rate_per_acre * float(crop.area_acres))
                unit, category, source = hist["unit"], hist["category"], "historical"
            elif default:
                estimated_need = round(default["rate_per_acre"] * float(crop.area_acres))
                unit, category, source = default["unit"], default["category"], "default"
            else:
                continue

            material_on_this_farm = farm_materials_by_name.get(material_name.lower())
            on_hand = material_on_this_farm.quantity_on_hand if material_on_this_farm else 0

            estimates.append({
                "material_name": material_name,
                "material": material_on_this_farm,
                "unit": unit,
                "category": category,
                "estimated_need": estimated_need,
                "on_hand": on_hand,
                "shortfall": max(estimated_need - on_hand, 0),
                "not_stocked": material_on_this_farm is None,
                "source": source,
            })

        if estimates:
            plans.append({"crop": crop, "estimates": estimates})

    return render(request, "demand_planning.html", {
        "plans": plans,
        "active_tab": "demand",
    })

from .forms import MaterialThresholdForm  # add to your existing forms import line


@login_required
def material_detail(request, pk):
    material = get_object_or_404(Material, pk=pk, farm__owner=request.user)

    purchase_form = MaterialPurchaseForm()
    usage_form = MaterialUsageForm(farm=material.farm)
    threshold_form = MaterialThresholdForm(instance=material)

    if request.method == "POST":
        if "log_purchase" in request.POST:
            purchase_form = MaterialPurchaseForm(request.POST)
            if purchase_form.is_valid():
                p = purchase_form.save(commit=False)
                p.material = material
                p.logged_by = request.user
                p.save()
                return redirect("stock:material_detail", pk=material.pk)
        elif "log_usage" in request.POST:
            usage_form = MaterialUsageForm(request.POST, farm=material.farm)
            if usage_form.is_valid():
                u = usage_form.save(commit=False)
                u.material = material
                u.logged_by = request.user
                u.save()
                return redirect("stock:material_detail", pk=material.pk)
        elif "update_threshold" in request.POST:
            threshold_form = MaterialThresholdForm(request.POST, instance=material)
            if threshold_form.is_valid():
                threshold_form.save()
                return redirect("stock:material_detail", pk=material.pk)

    return render(request, "material_detail.html", {
        "material": material,
        "purchases": material.purchases.all(),
        "usages": material.usages.select_related("crop"),
        "purchase_form": purchase_form,
        "usage_form": usage_form,
        "threshold_form": threshold_form,
        "active_tab": "materials",
    })


