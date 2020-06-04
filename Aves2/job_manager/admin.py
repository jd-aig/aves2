from django.contrib import admin
from job_manager.models import AvesJob, AvesWorker

# Register your models here.


class AvesJobAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'job_name',
        'username',
        'namespace',
        'status',
        'create_time',
        'update_time',
    )
    list_filter = ('namespace', 'username', 'status')
    search_fields = ('username', 'name')
    ordering = ('-id',)


class AvesWorkerAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'worker_name',
        'username',
        'namespace',
        'is_main_node',
        'entrypoint',
        'cpu_request',
        'mem_request',
        'gpu_request',
    )
    list_filter = ('namespace', 'username')
    ordering = ('-id',)


admin.site.register(AvesJob, AvesJobAdmin)
admin.site.register(AvesWorker, AvesWorkerAdmin)
