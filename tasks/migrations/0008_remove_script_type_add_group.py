# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0007_alter_taskconfig_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='taskconfig',
            name='script_type',
        ),
        migrations.AddField(
            model_name='taskconfig',
            name='group',
            field=models.CharField(blank=True, default='', help_text='任务分组，用于分类管理，如 数据同步、报表生成', max_length=100, verbose_name='分组'),
        ),
    ]
