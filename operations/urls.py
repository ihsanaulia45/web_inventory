from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sales-orders/", views.sales_orders, name="sales_orders"),
    path("sales-orders/", views.sales_orders, name="sales-orders"),
    path("sales-orders/export.csv", views.export_orders, name="export_orders"),
    path("sales-orders/<str:repeat_no>/", views.order_detail, name="order_detail"),
    path("sales-orders/<str:repeat_no>/", views.order_detail, name="order-detail"),
    path("sales-orders/<str:repeat_no>/remarks/", views.add_remark, name="add_remark"),
    path("trackers/<str:tracker_key>/", views.tracker_list, name="tracker_list"),
    path("trackers/<str:tracker_key>/", views.tracker_list, name="tracker"),
    path("trackers/<str:tracker_key>/export.csv", views.export_tracker, name="export_tracker"),
    path("shortage/", views.shortage_monitor, name="shortage_monitor"),
    path("shortage/", views.shortage_monitor, name="shortage-monitor"),
]
