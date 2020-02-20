import django_filters
from django.db.models import Q
from .models import User, K8SPvc, K8SPvcUserRel


class K8SPvcFilter(django_filters.rest_framework.FilterSet):
    user = django_filters.CharFilter(field_name="user", lookup_expr="exact", method="get_user_pvc")

    def get_user_pvc(self, queryset, key, name):
        return queryset.filter(user=User.objects.get(username=name).id)

    class Meta:
        model = K8SPvc
        fields = ["user"]

class K8SPvcUserRelFilter(django_filters.rest_framework.FilterSet):
    pvc = django_filters.NumberFilter(field_name="pvc", lookup_expr="exact", method="get_pvc_user")

    def get_pvc_user(self, queryset, key, name):
        return queryset.filter(pvc=name)

    class meta:
        model = K8SPvcUserRel
        fields = ['pvc']
