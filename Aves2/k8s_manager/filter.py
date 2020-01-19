import django_filters
from django.db.models import Q
from .models import K8SPvc, User

class K8SPvcFilter(django_filters.rest_framework.FilterSet):
    user = django_filters.CharFilter(name="user", lookup_expr= "")

    def get_user_pvc(self, queryset, name, value):
        return queryset.filter(user=User.objects.get(username=value).id)

    class Meta:
        model = User
        fields = ["user"]