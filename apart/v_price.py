from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator

from hier.models import Folder
from hier.utils import get_base_context, get_folder_id, process_common_commands
from .utils import next_period
from .models import Apart, Price, ELECTRICITY
from .forms import PriceForm


#----------------------------------
@login_required(login_url='account:login')
#----------------------------------
def price_list(request):
    process_common_commands(request)
    if not Apart.objects.filter(user = request.user.id, active = True).exists():
        return HttpResponseRedirect(reverse('apart:apart_list'))
    apart = get_object_or_404(Apart.objects.filter(user = request.user.id, active = True))
    data = Price.objects.filter(user = request.user.id).order_by('-period')
    if request.method != 'GET':
        page_number = 1
    else:
        page_number = request.GET.get('page')
    paginator = Paginator(data, 10)
    page_obj = paginator.get_page(page_number)
    folder_id = get_folder_id(request.user.id)
    context = get_base_context(request, folder_id, 0, _('pricess'), 'content_list')
    context['page_obj'] = page_obj
    template_file = 'apart/price_list.html'
    template = loader.get_template(template_file)
    return HttpResponse(template.render(context, request))

#----------------------------------
def price_add(request):
    apart = get_object_or_404(Apart.objects.filter(user = request.user.id, active = True))
    if (request.method == 'POST'):
        form = PriceForm(request.POST)
    else:
        if not Price.objects.filter(user = request.user.id).exists():
            period = next_period()
        else:
            last = Price.objects.filter(user = request.user.id).order_by('-period')[0]
            period = next_period(last.period)
        form = PriceForm(initial = { 'service': ELECTRICITY, 'period': period, 'tarif': 0, 'border': 0, 'tarif2': 0, 'border2': 0, 'tarif3': 0 })
    return show_page_form(request, 0, _('create a new price'), form, apart)

#----------------------------------
def price_form(request, pk):
    apart = get_object_or_404(Apart.objects.filter(user = request.user.id, active = True))
    data = get_object_or_404(Price.objects.filter(id = pk, user = request.user.id))
    if (request.method == 'POST'):
        form = PriceForm(request.POST, instance = data)
    else:
        form = PriceForm(instance = data)
    return show_page_form(request, pk, _('price'), form, apart)

#----------------------------------
@login_required(login_url='account:login')
#----------------------------------
def price_del(request, pk):
    apart = get_object_or_404(Apart.objects.filter(user = request.user.id, active = True))
    data = get_object_or_404(Price.objects.filter(id = pk, user = request.user.id))
    data.delete()
    return HttpResponseRedirect(reverse('apart:price_list'))


#----------------------------------
@login_required(login_url='account:login')
#----------------------------------
def show_page_form(request, pk, title, form, apart):
    if (request.method == 'POST'):
        if form.is_valid():
            data = form.save(commit = False)
            data.apart = apart
            form.save()
            return HttpResponseRedirect(reverse('apart:price_list'))
    folder_id = get_folder_id(request.user.id)
    context = get_base_context(request, folder_id, pk, title, form = form)
    template = loader.get_template('apart/price_form.html')
    return HttpResponse(template.render(context, request))