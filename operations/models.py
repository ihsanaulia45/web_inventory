from django.db import models
from django.db.models import Sum


class SalesOrder(models.Model):
    """One order-level snapshot; tonnage columns follow the workbook's SO values."""

    repeat_no = models.CharField(max_length=40, unique=True, db_index=True)
    order_no = models.CharField(max_length=80, blank=True, db_index=True)
    customer = models.CharField(max_length=120, blank=True, db_index=True)
    purchaser = models.CharField(max_length=120, blank=True, db_index=True)
    designation = models.CharField(max_length=80, blank=True, db_index=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    month_due_date = models.CharField(max_length=12, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    shipped = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    finishing_products = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    waiting_finish = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    in_process = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    raw_material_jsg = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    not_allotment = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    shortage_status = models.CharField(max_length=20, blank=True, db_index=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    imported_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "repeat_no"]
        indexes = [models.Index(fields=["customer", "due_date"], name="operations__custome_5f4520_idx")]

    def __str__(self):
        return f"{self.repeat_no} · {self.order_no}"

    @property
    def open_order(self):
        return max(self.quantity - self.shipped, 0)


class TrackerRecord(models.Model):
    """Shared fields for coil/material-level inventory records."""

    repeat_no = models.CharField(max_length=40, blank=True, db_index=True)
    coil_no = models.CharField(max_length=80, blank=True, db_index=True)
    weight = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    yard = models.CharField(max_length=80, blank=True, db_index=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    imported_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["repeat_no", "coil_no"]


class FinishGood(TrackerRecord):
    product_no = models.CharField(max_length=80, blank=True, db_index=True)
    customer = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=80, blank=True)
    grade = models.CharField(max_length=40, blank=True)
    finishing_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    ship_hold_reason = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.product_no or self.coil_no or str(self.pk)


class NotFinish(TrackerRecord):
    product_no = models.CharField(max_length=80, blank=True, db_index=True)
    customer = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=80, blank=True)
    final_line = models.CharField(max_length=80, blank=True)
    result_code = models.CharField(max_length=40, blank=True)
    ship_hold_reason = models.CharField(max_length=200, blank=True)
    finish_hold_reason = models.CharField(max_length=200, blank=True)
    count_ng = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.product_no or self.coil_no or str(self.pk)


class InProcess(TrackerRecord):
    customer = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=80, blank=True)
    coil_status = models.CharField(max_length=40, blank=True, db_index=True)
    leading_process = models.CharField(max_length=80, blank=True)
    post_process = models.CharField(max_length=80, blank=True)
    order_no = models.CharField(max_length=80, blank=True)
    due_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.coil_no or str(self.pk)


class RawMaterial(TrackerRecord):
    customer = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=80, blank=True)
    material_class = models.CharField(max_length=40, blank=True)
    ship_name = models.CharField(max_length=100, blank=True)
    maker_shipped_date = models.DateField(null=True, blank=True)
    accepted_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.coil_no or str(self.pk)


class ShortageDate(models.Model):
    repeat_no = models.CharField(max_length=40, unique=True, db_index=True)
    customer = models.CharField(max_length=120, blank=True)
    purchaser = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, blank=True, db_index=True)
    shortage_date = models.DateField(null=True, blank=True)
    remaining_stock = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    supply_until = models.CharField(max_length=12, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    imported_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.repeat_no} · {self.status}"


class ShortageRemark(models.Model):
    repeat_no = models.CharField(max_length=40, db_index=True)
    remarks = models.TextField(blank=True)
    input_by = models.CharField(max_length=100, blank=True)
    input_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-input_date", "-created_at"]

    def __str__(self):
        return f"{self.repeat_no}: {self.remarks[:50]}"


def dashboard_totals(queryset=None):
    """Aggregate SO snapshot values for dashboard cards; all quantities are tons."""
    orders = queryset if queryset is not None else SalesOrder.objects.all()
    values = orders.aggregate(
        order_tons=Sum("quantity"),
        shipped_tons=Sum("shipped"),
        finish_good_tons=Sum("finishing_products"),
        not_finish_tons=Sum("waiting_finish"),
        in_process_tons=Sum("in_process"),
        raw_material_tons=Sum("raw_material_jsg"),
        unallocated_tons=Sum("not_allotment"),
    )
    return {key: value or 0 for key, value in values.items()}
