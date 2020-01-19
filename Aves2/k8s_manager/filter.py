import django_filters
from django.db.models import Q
from .models import User, K8SPvc

class K8SPvcFilter(django_filters.rest_framework.FilterSet):
    user = django_filters.CharFilter(field_name="user", lookup_expr="exact", method="get_user_pvc")

    def get_user_pvc(self, queryset, name):
        print("进入get_user_pvc函数" + str(name))
        return queryset.filter(user=User.objects.get(username=name).id)

    class Meta:
        model = K8SPvc
        fields = ["user"]