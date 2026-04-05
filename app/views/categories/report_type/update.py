from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from app.models.report import ReportPeriodMonth


REPORT_TYPE_LABELS = {
    ReportPeriodMonth.ReportType.MONTH: "Báo cáo tháng",
    ReportPeriodMonth.ReportType.QUARTER: "Báo cáo quý",
    ReportPeriodMonth.ReportType.HALF_YEAR: "Báo cáo 6 tháng",
    ReportPeriodMonth.ReportType.NINE_MONTH: "Báo cáo 9 tháng",
    ReportPeriodMonth.ReportType.YEAR: "Báo cáo năm",
}

ALLOWED_OPTIONAL_TYPES = {
    ReportPeriodMonth.ReportType.QUARTER,
    ReportPeriodMonth.ReportType.HALF_YEAR,
    ReportPeriodMonth.ReportType.NINE_MONTH,
    ReportPeriodMonth.ReportType.YEAR,
}


@method_decorator(permission_required("app.change_reportperiodmonth"), name="dispatch")
class ReportPeriodMonthUpdateView(View):
    template_name = "categories/report_type/update.html"
    form_template_name = "categories/report_type/form.html"

    def get(self, request, *args, **kwargs):
        month = (request.GET.get("month") or "").strip()

        response = HttpResponse()
        response["HX-Redirect"] = reverse("report_period_month_list")

        if not month.isdigit():
            messages.warning(request, "Tháng không hợp lệ")
            return response

        month = int(month)
        if month < 1 or month > 12:
            messages.warning(request, "Tháng không hợp lệ")
            return response

        selected_report_types = list(
            ReportPeriodMonth.objects
            .filter(month=month)
            .values_list("report_type", flat=True)
        )

        if ReportPeriodMonth.ReportType.MONTH not in selected_report_types:
            selected_report_types.append(ReportPeriodMonth.ReportType.MONTH)

        return render(
            request,
            self.template_name,
            {
                "month": month,
                "selected_report_types": selected_report_types,
                "errors": {},
            },
            status=HTTPStatus.OK,
        )

    def post(self, request, *args, **kwargs):
        errors = {}
        month = (request.POST.get("month") or "").strip()
        response = HttpResponse()
        response["HX-Redirect"] = reverse("report_period_month_list")

        if not month.isdigit():
            messages.warning(request, "Tháng không hợp lệ")
            return response

        month = int(month)
        if month < 1 or month > 12:
            messages.warning(request, "Tháng không hợp lệ")
            return response

        submitted_types = request.POST.getlist("report_types")
        if not submitted_types:
            submitted_types = request.POST.getlist("report_types[]")

        submitted_types = [item.strip() for item in submitted_types if item.strip()]

        selected_types = {ReportPeriodMonth.ReportType.MONTH}
        for report_type in submitted_types:
            if report_type in ALLOWED_OPTIONAL_TYPES:
                selected_types.add(report_type)

        try:
            with transaction.atomic():
                current_types = set(
                    ReportPeriodMonth.objects
                    .filter(month=month)
                    .values_list("report_type", flat=True)
                )

                types_to_delete = current_types - selected_types
                if types_to_delete:
                    ReportPeriodMonth.objects.filter(
                        month=month,
                        report_type__in=types_to_delete,
                    ).delete()

                types_to_create = selected_types - current_types
                if types_to_create:
                    ReportPeriodMonth.objects.bulk_create(
                        [
                            ReportPeriodMonth(
                                month=month,
                                report_type=report_type,
                            )
                            for report_type in types_to_create
                        ]
                    )

            messages.success(request, f"Cập nhật loại báo cáo cho tháng {month} thành công")

            response = render(
                request,
                self.template_name,
                {
                    "month": month,
                    "selected_report_types": list(selected_types),
                    "errors": {},
                },
                status=HTTPStatus.OK,
            )
            response["HX-Trigger"] = "report-period-month:success"
            return response

        except Exception as e:
            messages.error(request, str(e))
            return render(
                request,
                self.template_name,
                {
                    "month": month,
                    "selected_report_types": list(selected_types),
                    "errors": errors,
                },
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )