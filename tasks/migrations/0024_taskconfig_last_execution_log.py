import django.db.models.deletion
from django.db import migrations, models


def fill_last_execution_logs(apps, schema_editor):
    """数据回填：为每个 TaskConfig 指向其最新一条 TaskExecutionLog"""
    TaskConfig = apps.get_model('tasks', 'TaskConfig')
    TaskExecutionLog = apps.get_model('tasks', 'TaskExecutionLog')
    from django.db.models import Max

    # 每个任务的最新日志 ID
    latest_ids = (
        TaskExecutionLog.objects
        .values('task_id')
        .annotate(latest_id=Max('id'))
    )
    for item in latest_ids:
        TaskConfig.objects.filter(pk=item['task_id']).update(
            last_execution_log_id=item['latest_id']
        )


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0023_add_script_args"),
    ]

    operations = [
        migrations.AddField(
            model_name="taskconfig",
            name="last_execution_log",
            field=models.ForeignKey(
                blank=True,
                help_text="指向该任务最新一条执行日志，每次创建日志时自动更新",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="tasks.taskexecutionlog",
                verbose_name="最近一次执行日志",
            ),
        ),
        migrations.RunPython(fill_last_execution_logs, migrations.RunPython.noop),
    ]
