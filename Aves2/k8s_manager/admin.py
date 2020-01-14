from django.contrib import admin
from k8s_manager.models import *

# Register your models here.

class UserAdmin(admin.ModelAdmin):
    pass


class K8SNamespaceAdmin(admin.ModelAdmin):
    pass


class K8SStorageClassAdmin(admin.ModelAdmin):
    pass


class K8SPvcAdmin(admin.ModelAdmin):
    pass


class K8SPvcUserRelAdmin(admin.ModelAdmin):
    pass


class K8SResourceQuotaAdmin(admin.ModelAdmin):
    pass


admin.site.register(User, UserAdmin)
admin.site.register(K8SNamespace, K8SNamespaceAdmin)
admin.site.register(K8SStorageClass, K8SStorageClassAdmin)
admin.site.register(K8SPvc, K8SPvcAdmin)
admin.site.register(K8SPvcUserRel, K8SPvcUserRelAdmin)
admin.site.register(K8SResourceQuota, K8SResourceQuotaAdmin)