import csv
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, IntegerField, Q, Sum, Value, When
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models.functions import Greatest
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from .models import (
    FinishGood,
    InProcess,
    NotFinish,
    RawMaterial,
    SalesOrder,
    ShortageDate,
    ShortageRemark,
    dashboard_totals,
)


TRACKERS = {
    "A": {"name": "Finish Good", "model": FinishGood, "order_field": "finishing_products"},
    "B": {"name": "Not Finish", "model": NotFinish, "order_field": "waiting_finish"},
    "C": {"name": "In Process", "model": InProcess, "order_field": "in_process"},
    "D": {"name": "Raw Material", "model": RawMaterial, "order_field": "raw_material_jsg"},
}


def _filtered_orders(params):
    orders = SalesOrder.objects.all()
    search = params.get("q", "").strip()
    customer = params.get("customer", "").strip()
    purchaser = params.get("purchaser", "").strip()
    designation = params.get("designation", "").strip()
    status = params.get("status", "").strip().upper()
    due_from = params.get("due_from", "").strip()
    due_to = params.get("due_to", "").strip()
    tracker = params.get("tracker", "").strip().upper()
    yard = params.get("yard", "").strip()
    period = params.get("period", "").strip()
    due_soon_only = params.get("due_soon", "") == "1"

    if search:
        order_match = (
            Q(repeat_no__icontains=search)
            | Q(order_no__icontains=search)
            | Q(customer__icontains=search)
            | Q(purchaser__icontains=search)
            | Q(designation__icontains=search)
        )
        for tracker_config in TRACKERS.values():
            related = tracker_config["model"].objects.filter(
                repeat_no__in=orders.values("repeat_no")
            ).filter(Q(coil_no__icontains=search) | Q(product_no__icontains=search) if tracker_config["model"] in {FinishGood, NotFinish} else Q(coil_no__icontains=search))
            order_match |= Q(repeat_no__in=related.values("repeat_no"))
        orders = orders.filter(order_match)
    if customer:
        orders = orders.filter(customer__icontains=customer)
    if purchaser:
        orders = orders.filter(purchaser__icontains=purchaser)
    if designation:
        orders = orders.filter(designation__icontains=designation)
    if status:
        orders = orders.filter(shortage_status__iexact=status)
    if due_from:
        try:
            date.fromisoformat(due_from)
            orders = orders.filter(due_date__gte=due_from)
        except ValueError:
            pass
    if due_to:
        try:
            date.fromisoformat(due_to)
            orders = orders.filter(due_date__lte=due_to)
        except ValueError:
            pass
    if period == "this-month":
        current = timezone.localdate()
        orders = orders.filter(due_date__year=current.year, due_date__month=current.month)
    elif period == "next-30":
        current = timezone.localdate()
        orders = orders.filter(due_date__gte=current, due_date__lte=current + timedelta(days=30))
    if due_soon_only:
        current = timezone.localdate()
        orders = orders.filter(due_date__gte=current, due_date__lte=current + timedelta(days=7))
    if tracker in TRACKERS:
        tracker_field = TRACKERS[tracker]["order_field"]
        orders = orders.filter(**{f"{tracker_field}__gt": 0})
    elif tracker == "SHIPPED":
        orders = orders.filter(shipped__gt=0)
    elif tracker == "UNALLOCATED":
        orders = orders.filter(not_allotment__gt=0)
    if yard:
        matching = set()
        for tracker_config in TRACKERS.values():
            matching.update(
                tracker_config["model"].objects.filter(yard__icontains=yard)
                .values_list("repeat_no", flat=True)
            )
        orders = orders.filter(repeat_no__in=matching)
    return orders.distinct()


def _filter_values(request):
    values = {
        key: request.GET.get(key, "")
        for key in ("q", "customer", "purchaser", "designation", "status", "due_from", "due_to", "period", "tracker", "yard")
    }
    values["active_count"] = sum(bool(value) for key, value in values.items() if key != "active_count")
    return values


def _hydrate_record(record):
    """Expose original workbook field names to templates while retaining typed model fields."""
    aliases = {
        "coil_no": "jsg_coil_no",
        "product_no": "jsg_product_no",
        "yard": "yard_c_r_s",
        "grade": "target_grade_cd",
        "result_code": "rslt_cd",
        "material_class": "class_name",
        "accepted_date": "jsg_accept_date",
        "ship_hold_reason": "ship_hold_reason",
    }
    payload = getattr(record, "raw_payload", {}) or {}
    for field_name, source_name in aliases.items():
        if source_name in payload:
            setattr(record, source_name, payload[source_name])
    for key, value in payload.items():
        if not hasattr(record, key):
            setattr(record, key, value)
    return record


def _hydrate_order(order):
    payload = order.raw_payload or {}
    for key, value in payload.items():
        if not hasattr(order, key):
            setattr(order, key, value)
    return order


def _shortage_for(repeat_no):
    return ShortageDate.objects.filter(repeat_no=repeat_no).first()


def _priority(queryset):
    return queryset.annotate(
        status_rank=Case(
            When(shortage_status__iexact="SHORTAGE", then=Value(0)),
            When(shortage_status__iexact="WARNING", then=Value(1)),
            When(shortage_status__iexact="SAFE", then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    ).order_by("status_rank", "due_date", "-not_allotment", "repeat_no")


@login_required
def dashboard(request):
    orders = _filtered_orders(request.GET)
    today = timezone.localdate()
    due_soon = orders.filter(due_date__gte=today, due_date__lte=today + timedelta(days=7)).count()
    totals = dashboard_totals(orders)
    open_order_total = orders.aggregate(
        total=Sum(
            Greatest(
                ExpressionWrapper(F("quantity") - F("shipped"), output_field=DecimalField(max_digits=14, decimal_places=3)),
                Value(0),
                output_field=DecimalField(max_digits=14, decimal_places=3),
            )
        )
    )["total"] or Decimal("0")
    shortage_counts = {
        key: orders.filter(shortage_status__iexact=status).count()
        for key, status in (("shortage", "SHORTAGE"), ("warning", "WARNING"), ("safe", "SAFE"))
    }
    shortage_counts["total"] = sum(shortage_counts.values())
    shortage_counts["due_soon"] = due_soon
    tracker_counts = {
        "A_count": orders.filter(finishing_products__gt=0).count(),
        "B_count": orders.filter(waiting_finish__gt=0).count(),
        "C_count": orders.filter(in_process__gt=0).count(),
        "D_count": orders.filter(raw_material_jsg__gt=0).count(),
    }
    tracker_totals = {
        "A": totals["finish_good_tons"],
        "B": totals["not_finish_tons"],
        "C": totals["in_process_tons"],
        "D": totals["raw_material_tons"],
    }
    kpis = {
        "open_order": open_order_total,
        "total_quantity": totals["order_tons"],
        "shipped": totals["shipped_tons"],
        "unallocated": totals["unallocated_tons"],
        "shipped_percent": (float(totals["shipped_tons"] / totals["order_tons"] * 100) if totals["order_tons"] else 0),
        "due_soon": due_soon,
        "order_count": orders.count(),
    }
    yard_summary = []
    for tracker_key, config in TRACKERS.items():
        rows = config["model"].objects.filter(repeat_no__in=orders.values("repeat_no"))
        for item in rows.values("yard").annotate(total=Sum("weight")).order_by("yard"):
            if item["yard"]:
                yard_summary.append({"yard": item["yard"], "total": item["total"] or 0, "tracker": tracker_key})
    total_tracker = sum(tracker_totals.values())
    chart = {
        key.lower(): round(float(value / total_tracker * 100), 1) if total_tracker else 0
        for key, value in tracker_totals.items()
    }
    chart["total"] = total_tracker
    shortage_bars = {
        key: round(value / shortage_counts["total"] * 100, 1) if shortage_counts["total"] else 0
        for key, value in shortage_counts.items()
        if key in {"shortage", "warning", "safe"}
    }
    open_expression = Greatest(
        ExpressionWrapper(F("quantity") - F("shipped"), output_field=DecimalField(max_digits=14, decimal_places=3)),
        Value(0),
        output_field=DecimalField(max_digits=14, decimal_places=3),
    )
    monthly_summary = list(
        orders.exclude(month_due_date="")
        .values("month_due_date")
        .annotate(order_count=Count("pk"), open_tons=Sum(open_expression))
        .order_by("month_due_date")
    )
    legacy_metrics = {
        "open_order": kpis["open_order"],
        "order_count": kpis["order_count"],
        "total_quantity": kpis["total_quantity"],
        "shipped": kpis["shipped"],
        "shipped_percent": kpis["shipped_percent"],
        "finish_good": tracker_totals["A"],
        "not_finish": tracker_totals["B"],
        "in_process": tracker_totals["C"],
        "raw_material": tracker_totals["D"],
        "finish_good_count": FinishGood.objects.filter(repeat_no__in=orders.values("repeat_no")).count(),
        "not_finish_count": NotFinish.objects.filter(repeat_no__in=orders.values("repeat_no")).count(),
        "in_process_count": InProcess.objects.filter(repeat_no__in=orders.values("repeat_no")).count(),
        "raw_material_count": RawMaterial.objects.filter(repeat_no__in=orders.values("repeat_no")).count(),
        "tracker_total": total_tracker,
    }
    context = {
        "page_title": "Dashboard Product Operation",
        "active_nav": "dashboard",
        "kpis": kpis,
        "shortage_counts": shortage_counts,
        "tracker_totals": tracker_totals,
        "tracker_counts": tracker_counts,
        "metrics": legacy_metrics,
        "shortage": shortage_counts,
        "chart": chart,
        "tracker_chart": chart,
        "shortage_bars": shortage_bars,
        "as_of_date": today,
        "customers": orders.order_by("customer").values_list("customer", flat=True).distinct(),
        "purchasers": orders.order_by("purchaser").values_list("purchaser", flat=True).distinct(),
        "priority_orders": _priority(orders)[:10],
        "yard_summary": yard_summary[:12],
        "monthly_summary": monthly_summary,
        "monthly_max_open": max((float(row["open_tons"] or 0) for row in monthly_summary), default=0),
        "recent_orders": orders.order_by("-imported_at")[:8],
        "filters": _filter_values(request),
    }
    return render(request, "operations/dashboard.html", context)


@login_required
def sales_orders(request):
    orders = _priority(_filtered_orders(request.GET))
    if request.GET.get("sort") == "quantity":
        orders = orders.order_by("-quantity", "due_date")
    elif request.GET.get("sort") == "open_order":
        orders = orders.annotate(
            open_balance=Greatest(
                ExpressionWrapper(F("quantity") - F("shipped"), output_field=DecimalField(max_digits=14, decimal_places=3)),
                Value(0),
                output_field=DecimalField(max_digits=14, decimal_places=3),
            )
        ).order_by("-open_balance", "due_date")
    elif request.GET.get("sort") == "due_date":
        orders = orders.order_by("due_date", "repeat_no")
    paginator = Paginator(orders, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "operations/sales_orders.html",
        {
            "page_title": "Sales Orders",
            "active_nav": "sales_orders",
            "orders": page,
            "page_obj": page,
            "filters": _filter_values(request),
            "customers": SalesOrder.objects.order_by("customer").values_list("customer", flat=True).distinct(),
        },
    )


@login_required
def order_detail(request, repeat_no):
    order = get_object_or_404(SalesOrder, repeat_no=repeat_no)
    _hydrate_order(order)
    tracker_rows = {
        "A": [_hydrate_record(row) for row in FinishGood.objects.filter(repeat_no=repeat_no)],
        "B": [_hydrate_record(row) for row in NotFinish.objects.filter(repeat_no=repeat_no)],
        "C": [_hydrate_record(row) for row in InProcess.objects.filter(repeat_no=repeat_no)],
        "D": [_hydrate_record(row) for row in RawMaterial.objects.filter(repeat_no=repeat_no)],
    }
    remarks = list(ShortageRemark.objects.filter(repeat_no=repeat_no))
    tracker_counts = {
        "finish_good": len(tracker_rows["A"]),
        "not_finish": len(tracker_rows["B"]),
        "in_process": len(tracker_rows["C"]),
        "raw_material": len(tracker_rows["D"]),
    }
    tracker_exceptions = {
        "finish_good": sum(bool(row.ship_hold_reason) for row in tracker_rows["A"]),
        "not_finish": sum(bool(row.ship_hold_reason or row.finish_hold_reason or row.count_ng) for row in tracker_rows["B"]),
    }
    quantity = float(order.quantity or 0)
    allocation = {
        "shipped_pct": round(float(order.shipped or 0) / quantity * 100, 1) if quantity else 0,
        "a_pct": round(float(order.finishing_products or 0) / quantity * 100, 1) if quantity else 0,
        "b_pct": round(float(order.waiting_finish or 0) / quantity * 100, 1) if quantity else 0,
        "c_pct": round(float(order.in_process or 0) / quantity * 100, 1) if quantity else 0,
        "d_pct": round(float(order.raw_material_jsg or 0) / quantity * 100, 1) if quantity else 0,
    }
    shortage = _shortage_for(repeat_no)
    if shortage:
        _hydrate_order(shortage)
    return render(
        request,
        "operations/order_detail.html",
        {
            "page_title": f"Sales Order {order.order_no or order.repeat_no}",
            "active_nav": "sales_orders",
            "order": order,
            "tracker_rows": tracker_rows,
            "tracker_records": {"fg": tracker_rows["A"], "nf": tracker_rows["B"], "ip": tracker_rows["C"], "rm": tracker_rows["D"]},
            "tracker_counts": tracker_counts,
            "tracker_exceptions": tracker_exceptions,
            "allocation": allocation,
            "shortage": shortage,
            "remarks": remarks,
            "remark": remarks[0] if remarks else None,
        },
    )


@require_POST
@login_required
def add_remark(request, repeat_no):
    get_object_or_404(SalesOrder, repeat_no=repeat_no)
    remark = request.POST.get("remarks", "").strip()
    if remark:
        ShortageRemark.objects.create(
            repeat_no=repeat_no,
            remarks=remark,
            input_by=request.user.get_username() if request.user.is_authenticated else "planner",
            input_date=timezone.now(),
        )
        messages.success(request, "Catatan tindak lanjut berhasil ditambahkan.")
    return redirect("order_detail", repeat_no=repeat_no)


@login_required
def tracker_list(request, tracker_key):
    tracker_key = {
        "finish-good": "A", "not-finish": "B", "in-process": "C", "raw-material": "D"
    }.get(tracker_key.lower(), tracker_key.upper())
    config = TRACKERS.get(tracker_key)
    if not config:
        return redirect("dashboard")
    model = config["model"]
    rows = model.objects.all()
    search = request.GET.get("q", "").strip()
    yard = request.GET.get("yard", "").strip()
    repeat_no = request.GET.get("repeat_no", "").strip()
    if search:
        search_query = Q(repeat_no__icontains=search) | Q(coil_no__icontains=search) | Q(customer__icontains=search) | Q(designation__icontains=search)
        if model in {FinishGood, NotFinish}:
            search_query |= Q(product_no__icontains=search)
        rows = rows.filter(search_query)
    if yard:
        rows = rows.filter(yard__icontains=yard)
    if repeat_no:
        rows = rows.filter(repeat_no=repeat_no)
    paginator = Paginator(rows, 25)
    page = paginator.get_page(request.GET.get("page"))
    hydrated_rows = [_hydrate_record(row) for row in page.object_list]
    page.object_list = hydrated_rows
    yards = model.objects.exclude(yard="").order_by("yard").values_list("yard", flat=True).distinct()
    return render(
        request,
        "operations/tracker_list.html",
        {
            "page_title": f"{tracker_key}. {config['name']}",
            "active_nav": "trackers",
            "tracker_key": tracker_key,
            "tracker_name": config["name"],
            "rows": page,
            "page_obj": page,
            "filters": {
                "q": search,
                "yard": yard,
                "repeat_no": repeat_no,
                "active_count": sum(bool(value) for value in (search, yard, repeat_no)),
            },
            "yards": yards,
            "statuses": [],
            "filter_count": sum(bool(value) for value in (search, yard, repeat_no)),
            "filters_active_count": sum(bool(value) for value in (search, yard, repeat_no)),
            "total_weight": rows.aggregate(total=Sum("weight"))["total"] or 0,
            "total_count": rows.count(),
        },
    )


@login_required
def shortage_monitor(request):
    filtered = _filtered_orders(request.GET)
    orders = _priority(filtered.filter(shortage_status__in=["SHORTAGE", "WARNING"]))
    paginator = Paginator(orders, 20)
    page = paginator.get_page(request.GET.get("page"))
    shortage_by_repeat = {item.repeat_no: item for item in ShortageDate.objects.filter(repeat_no__in=orders.values("repeat_no"))}
    latest_remarks = {}
    for remark in ShortageRemark.objects.filter(repeat_no__in=orders.values("repeat_no")):
        latest_remarks.setdefault(remark.repeat_no, remark)
    shortage_rows = []
    for order in page.object_list:
        item = shortage_by_repeat.get(order.repeat_no)
        if item:
            item.remark = latest_remarks.get(order.repeat_no).remarks if latest_remarks.get(order.repeat_no) else ""
            shortage_rows.append(item)
    counts = {
        "shortage": filtered.filter(shortage_status__iexact="SHORTAGE").count(),
        "warning": filtered.filter(shortage_status__iexact="WARNING").count(),
        "safe": filtered.filter(shortage_status__iexact="SAFE").count(),
    }
    return render(
        request,
        "operations/shortage_monitor.html",
        {
            "page_title": "Shortage Monitor",
            "active_nav": "shortage",
            "orders": page,
            "shortage_rows": shortage_rows,
            "counts": counts,
            "page_obj": page,
            "shortage_by_repeat": shortage_by_repeat,
            "filters": _filter_values(request),
        },
    )


@login_required
def export_orders(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="sales_orders.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Repeat No", "Sales Order", "Customer", "Purchaser", "Designation", "Due Date", "Quantity (t)", "Shipped (t)", "Open Order (t)", "A Finish Good (t)", "B Not Finish (t)", "C In Process (t)", "D Raw Material (t)", "Unallocated (t)", "Shortage Status"])
    for order in _priority(_filtered_orders(request.GET).order_by("due_date", "repeat_no")):
        writer.writerow([order.repeat_no, order.order_no, order.customer, order.purchaser, order.designation, order.due_date, order.quantity, order.shipped, order.open_order, order.finishing_products, order.waiting_finish, order.in_process, order.raw_material_jsg, order.not_allotment, order.shortage_status])
    return response


@login_required
def export_tracker(request, tracker_key):
    tracker_key = tracker_key.upper()
    config = TRACKERS.get(tracker_key)
    if not config:
        return redirect("dashboard")
    rows = config["model"].objects.all()
    if request.GET.get("q"):
        q = request.GET["q"].strip()
        search_query = Q(repeat_no__icontains=q) | Q(coil_no__icontains=q) | Q(customer__icontains=q) | Q(designation__icontains=q)
        if config["model"] in {FinishGood, NotFinish}:
            search_query |= Q(product_no__icontains=q)
        rows = rows.filter(search_query)
    if request.GET.get("yard"):
        rows = rows.filter(yard__icontains=request.GET["yard"].strip())
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="tracker_{tracker_key.lower()}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Repeat No", "Coil No", "Weight (t)", "Yard", "Details"])
    for row in rows:
        writer.writerow([row.repeat_no, row.coil_no, row.weight, row.yard, row.raw_payload])
    return response
