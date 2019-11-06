from django.contrib import admin
from job_manager.models import AvesJob, K8SWorker

# Register your models here.

class AvesJobAdmin(admin.ModelAdmin):
    pass


class K8SWorkerAdmin(admin.ModelAdmin):
    pass


admin.site.register(AvesJob, AvesJobAdmin)
admin.site.register(K8SWorker, K8SWorkerAdmin)
