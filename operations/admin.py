from django.contrib import admin

from .models import FinishGood, InProcess, NotFinish, RawMaterial, SalesOrder, ShortageDate, ShortageRemark


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("repeat_no", "order_no", "customer", "purchaser", "due_date", "quantity", "shipped", "shortage_status")
    list_filter = ("shortage_status", "customer", "purchaser", "due_date")
    search_fields = ("repeat_no", "order_no", "customer", "purchaser")
    ordering = ("due_date", "repeat_no")


@admin.register(FinishGood)
class FinishGoodAdmin(admin.ModelAdmin):
    list_display = ("product_no", "coil_no", "repeat_no", "customer", "grade", "weight", "yard")
    search_fields = ("product_no", "coil_no", "repeat_no", "customer")
    list_filter = ("grade", "yard")


@admin.register(NotFinish)
class NotFinishAdmin(admin.ModelAdmin):
    list_display = ("product_no", "coil_no", "repeat_no", "customer", "final_line", "count_ng", "yard")
    search_fields = ("product_no", "coil_no", "repeat_no", "customer")
    list_filter = ("final_line", "yard")


@admin.register(InProcess)
class InProcessAdmin(admin.ModelAdmin):
    list_display = ("coil_no", "repeat_no", "customer", "coil_status", "leading_process", "weight", "yard")
    search_fields = ("coil_no", "repeat_no", "customer", "order_no")
    list_filter = ("coil_status", "leading_process", "yard")


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ("coil_no", "repeat_no", "customer", "designation", "material_class", "weight", "yard")
    search_fields = ("coil_no", "repeat_no", "customer", "designation")
    list_filter = ("material_class", "yard", "ship_name")


@admin.register(ShortageDate)
class ShortageDateAdmin(admin.ModelAdmin):
    list_display = ("repeat_no", "customer", "status", "shortage_date", "remaining_stock")
    list_filter = ("status", "customer")
    search_fields = ("repeat_no", "customer", "purchaser")


@admin.register(ShortageRemark)
class ShortageRemarkAdmin(admin.ModelAdmin):
    list_display = ("repeat_no", "input_by", "input_date")
    search_fields = ("repeat_no", "remarks", "input_by")
    list_filter = ("input_by",)
