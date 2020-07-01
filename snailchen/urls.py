"""snailchen URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
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
from django.urls import path

from abitur.views import AbiturView, UpdateView, AjaxCheckedView, AjaxWinnerView, HomeView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('update/', UpdateView.as_view(), name='update'),
    path('abitur/', AbiturView.as_view(), name='abitur'),
    path('olympics-checked/', AjaxCheckedView.as_view(), name='check-student'),
    path('olympics-winner/', AjaxWinnerView.as_view(), name='olympics-winner'),
    path('', HomeView.as_view(), name='home')
]
