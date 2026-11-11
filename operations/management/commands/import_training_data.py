"""Import the provided training workbook as replaceable current-state snapshots."""
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook

from operations.models import (
    FinishGood,
    InProcess,
    NotFinish,
    RawMaterial,
    SalesOrder,
    ShortageDate,
    ShortageRemark,
)


def clean_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def get(row, *names, default=None):
    for name in names:
        value = row.get(name)
        if value is not None and value != "":
            return value
    return default


def as_text(value):
    return "" if value is None else str(value).strip()


def as_decimal(value):
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value)).quantize(Decimal("0.001"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def read_sheet(workbook, title):
    if title not in workbook.sheetnames:
        return []
    sheet = workbook[title]
    iterator = sheet.iter_rows(values_only=True)
    headers = next(iterator, ())
    headers = [str(header).strip() if header is not None else "" for header in headers]
    output = []
    for values in iterator:
        if not any(value is not None for value in values):
            continue
        row = {headers[index]: value for index, value in enumerate(values) if index < len(headers) and headers[index]}
        output.append(row)
    return output


class Command(BaseCommand):
    help = "Import Sales Order and A–D tracker snapshots from an XLSX workbook."

    def add_arguments(self, parser):
        parser.add_argument(
            "workbook",
            nargs="?",
            default="Data/Training Web.xlsx",
            help="Workbook path (default: Data/Training Web.xlsx)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["workbook"]).expanduser()
        if not path.exists():
            raise CommandError(f"Workbook not found: {path}")
        try:
            workbook = load_workbook(path, read_only=True, data_only=True)
        except Exception as exc:
            raise CommandError(f"Cannot read workbook: {exc}") from exc

        rows = {name: read_sheet(workbook, name) for name in (
            "Sales_Order", "Finish_Good", "Not_Finish", "In_Process", "Raw_Material",
            "Shortage_Date", "Shortage_Remark",
        )}

        orders = []
        shortage_status = {as_text(row.get("repeat_no")): as_text(row.get("status")) for row in rows["Shortage_Date"]}
        for row in rows["Sales_Order"]:
            repeat_no = as_text(row.get("repeat_no"))
            if not repeat_no:
                continue
            orders.append(SalesOrder(
                repeat_no=repeat_no,
                order_no=as_text(get(row, "order_no", "order_no1")),
                customer=as_text(row.get("customer")),
                purchaser=as_text(get(row, "purchaser", "purchacer")),
                designation=as_text(row.get("designation")),
                due_date=as_date(row.get("due_date")),
                month_due_date=as_text(row.get("month_due_date")),
                quantity=as_decimal(row.get("quantity")),
                shipped=as_decimal(row.get("shipped")),
                finishing_products=as_decimal(row.get("finishing_products")),
                waiting_finish=as_decimal(row.get("waiting_finish")),
                in_process=as_decimal(row.get("in_process")),
                raw_material_jsg=as_decimal(row.get("raw_material_jsg")),
                not_allotment=as_decimal(row.get("not_allotment")),
                shortage_status=shortage_status.get(repeat_no, ""),
                raw_payload={key: clean_value(value) for key, value in row.items()},
            ))

        def tracker_records(sheet_name, model, mapper):
            records = []
            for row in rows[sheet_name]:
                repeat_no = as_text(row.get("repeat_no"))
                values = {
                    "repeat_no": repeat_no,
                    "coil_no": as_text(get(row, "jsg_coil_no", "coil_no")),
                    "weight": as_decimal(row.get("weight")) if row.get("weight") not in (None, "") else None,
                    "yard": as_text(get(row, "yard_c_r_s", "yard")),
                    "raw_payload": {key: clean_value(value) for key, value in row.items()},
                }
                values.update(mapper(row))
                records.append(model(**values))
            return records

        finish_goods = tracker_records("Finish_Good", FinishGood, lambda row: {
            "product_no": as_text(row.get("jsg_product_no")),
            "customer": as_text(row.get("customer")),
            "designation": as_text(row.get("designation")),
            "grade": as_text(row.get("target_grade_cd")),
            "finishing_date": as_date(row.get("finishing_date")),
            "due_date": as_date(row.get("order_due_date")),
            "ship_hold_reason": as_text(row.get("ship_hold_reason")),
        })
        not_finish = tracker_records("Not_Finish", NotFinish, lambda row: {
            "product_no": as_text(row.get("jsg_product_no")),
            "customer": as_text(row.get("customer")),
            "designation": as_text(get(row, "jsg_designation", "designation")),
            "final_line": as_text(row.get("final_line")),
            "result_code": as_text(row.get("rslt_cd")),
            "ship_hold_reason": as_text(row.get("ship_hold_reason")),
            "finish_hold_reason": as_text(row.get("finish_hold_reason")),
            "count_ng": int(as_decimal(row.get("count_ng"))),
        })
        in_process = tracker_records("In_Process", InProcess, lambda row: {
            "customer": as_text(row.get("customer")),
            "designation": as_text(row.get("designation")),
            "coil_status": as_text(row.get("coil_status")),
            "leading_process": as_text(row.get("leading_process")),
            "post_process": as_text(row.get("post_process")),
            "order_no": as_text(get(row, "order_no1", "order_no")),
            "due_date": as_date(row.get("order_due_date")),
        })
        raw_material = tracker_records("Raw_Material", RawMaterial, lambda row: {
            "customer": as_text(row.get("customer")),
            "designation": as_text(get(row, "raw_material_designation", "designation_jsg")),
            "material_class": as_text(row.get("class_name")),
            "ship_name": as_text(row.get("ship_name")),
            "maker_shipped_date": as_date(row.get("maker_shipped_date")),
            "accepted_date": as_date(get(row, "jsg_accept_date", "outside_warehouse_accept_date")),
        })

        shortage_dates = []
        for row in rows["Shortage_Date"]:
            repeat_no = as_text(row.get("repeat_no"))
            if not repeat_no:
                continue
            shortage_dates.append(ShortageDate(
                repeat_no=repeat_no,
                customer=as_text(row.get("customer")),
                purchaser=as_text(row.get("purchaser")),
                status=as_text(row.get("status")),
                shortage_date=as_date(row.get("shortage_date")),
                remaining_stock=as_decimal(row.get("remaining_stock")) if row.get("remaining_stock") not in (None, "") else None,
                supply_until=as_text(row.get("supply_until")),
                raw_payload={key: clean_value(value) for key, value in row.items()},
            ))

        remarks = []
        for row in rows["Shortage_Remark"]:
            repeat_no = as_text(row.get("repeat_no"))
            if repeat_no:
                remarks.append(ShortageRemark(
                    repeat_no=repeat_no,
                    remarks=as_text(row.get("remarks")),
                    input_by=as_text(row.get("input_by")),
                    input_date=row.get("input_date") if isinstance(row.get("input_date"), datetime) else None,
                ))

        model_rows = [
            (SalesOrder, orders), (FinishGood, finish_goods), (NotFinish, not_finish),
            (InProcess, in_process), (RawMaterial, raw_material),
            (ShortageDate, shortage_dates), (ShortageRemark, remarks),
        ]
        for model, objects in model_rows:
            model.objects.all().delete()
            if objects:
                model.objects.bulk_create(objects, batch_size=500)

        totals = ", ".join(f"{model.__name__}: {len(objects)}" for model, objects in model_rows)
        self.stdout.write(self.style.SUCCESS(f"Imported {path.name}. {totals}"))
