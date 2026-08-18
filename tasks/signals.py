from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import TaskConfig
from .scheduler import register_task, unregister_task


@receiver(post_save, sender=TaskConfig)
def on_task_config_saved(sender, instance, **kwargs):
    """TaskConfig 创建或修改后，自动同步到调度器（延迟到事务提交以确保 M2M 已保存）"""
    def _sync():
        if instance.is_active:
            register_task(instance)
        else:
            unregister_task(instance)
    transaction.on_commit(_sync)


@receiver(post_delete, sender=TaskConfig)
def on_task_config_deleted(sender, instance, **kwargs):
    """TaskConfig 删除后，从调度器移除"""
    unregister_task(instance)