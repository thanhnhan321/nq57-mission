import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from app.tasks.mission import (
    enqueue_create_mission_reports,
    run_create_mission_reports_sync,
    enqueue_update_mission_overdue_status_for_date,
    run_update_mission_overdue_status_sync,
)


@csrf_exempt
@require_POST
def mission_run_task_api(request):
    """
    POST /app/mission/run-task/

    Body:
    {
        "report_year": 2026,
        "report_month": 4,
        "run_type": "sync"   // optional: async | sync
    }
    """
    try:
        body = json.loads(request.body or "{}")

        report_year = int(body.get("report_year"))
        report_month = int(body.get("report_month"))
        run_type = (body.get("run_type") or "async").lower()

        if run_type not in ["async", "sync"]:
            return JsonResponse(
                {"success": False, "message": "run_type must be 'async' or 'sync'"},
                status=400,
            )

        if run_type == "sync":
            result = run_create_mission_reports_sync(
                report_year=report_year,
                report_month=report_month,
            )
            return JsonResponse(
                {
                    "success": True,
                    "task": "create_monthly_mission_reports",
                    "run_type": "sync",
                    "report_year": report_year,
                    "report_month": report_month,
                    "result": result,
                },
                status=200,
            )

        task = enqueue_create_mission_reports(
            report_year=report_year,
            report_month=report_month,
        )
        return JsonResponse(
            {
                "success": True,
                "task": "create_monthly_mission_reports",
                "run_type": "async",
                "report_year": report_year,
                "report_month": report_month,
                "task_id": str(task.id),
                "message": "Mission report creation task queued successfully",
            },
            status=200,
        )

    except TypeError:
        return JsonResponse(
            {"success": False, "message": "report_year and report_month are required"},
            status=400,
        )
    except ValueError as e:
        return JsonResponse(
            {"success": False, "message": str(e)},
            status=400,
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "message": "Failed to run mission task",
                "error": str(e),
            },
            status=500,
        )


@csrf_exempt
@require_POST
def mission_run_overdue_status_task_api(request):
    """
    POST /app/mission/run-overdue-status-task/

    Body:
    {
        "base_date": "2026-04-03",   // optional, default = today
        "run_type": "sync"           // optional: async | sync
    }
    """
    try:
        body = json.loads(request.body or "{}")

        base_date = body.get("base_date")
        run_type = (body.get("run_type") or "async").lower()

        if run_type not in ["async", "sync"]:
            return JsonResponse(
                {"success": False, "message": "run_type must be 'async' or 'sync'"},
                status=400,
            )

        if run_type == "sync":
            result = run_update_mission_overdue_status_sync(base_date)
            return JsonResponse(
                {
                    "success": True,
                    "task": "update_mission_overdue_status_daily",
                    "run_type": "sync",
                    "base_date": base_date,
                    "result": result,
                },
                status=200,
            )

        task = enqueue_update_mission_overdue_status_for_date(base_date)
        return JsonResponse(
            {
                "success": True,
                "task": "update_mission_overdue_status_daily",
                "run_type": "async",
                "base_date": base_date,
                "task_id": str(task.id),
                "message": "Mission overdue status update task queued successfully",
            },
            status=200,
        )

    except ValueError as e:
        return JsonResponse(
            {"success": False, "message": str(e)},
            status=400,
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "message": "Failed to run overdue status task",
                "error": str(e),
            },
            status=500,
        )