from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
import views

urlpatterns = [
    url(r'^$',        views.index,       name='index'),
    url(r'^login/$',  auth_views.login,  name='login'),
    #url(r'^logout/$', auth_views.logout, name='logout'),
    url(r'^logout/$', auth_views.logout, {'next_page': '/'}, name='logout'),
    url(r'^trip/',    include('trip.urls',   namespace="trip")),
    url(r'^fuel/',    include('fuel.urls',   namespace="fuel")),
    url(r'^apart/',   include('apart.urls',  namespace="apart")),
    url(r'^proj/',    include('proj.urls',   namespace="proj")),
    url(r'^task/',    include('task.urls',   namespace="task")),
    url(r'^pir/',     include('pir.urls',    namespace="pir")),
    url(r'^admin/',   include(admin.site.urls)),
]