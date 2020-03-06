from django.conf import settings


def url_prefix(request):

    context = {'url_prefix': settings.URL_PREFIX}

    return context
