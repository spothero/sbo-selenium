from django.conf import settings
from django.conf.urls import url, patterns
from django.conf.urls.static import static
from django.views.generic import TemplateView


urlpatterns = patterns('',
    url(r'^good_accessibility/$', TemplateView.as_view(template_name='sbo_selenium/good_accessibility.html'), {}, 'good_accessibility'),
    url(r'^poor_accessibility/$', TemplateView.as_view(template_name='sbo_selenium/poor_accessibility.html'), {}, 'poor_accessibility'),
) + static(settings.STATIC_URL, settings.STATIC_ROOT)
