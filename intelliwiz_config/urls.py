"""intelliwiz_config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from apps.peoples.views import SignIn, SignOut
import debug_toolbar
urlpatterns = [
    path('', SignIn.as_view(), name='login'),
    path('logout/', SignOut.as_view(), name='logout'),
    path('dashboard/', login_required(TemplateView.as_view(template_name='base_ajax.html')), name='home'),
    path('admin/', admin.site.urls),
    path('__debug__/', include(debug_toolbar.urls)), #shoul use when debug=True
    path('select2/', include('django_select2.urls')),
    path('onboarding/', include('apps.onboarding.urls')),
    path('peoples/', include('apps.peoples.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)