from datetime import datetime, timedelta
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect, FileResponse, HttpResponseNotFound
from django.template import loader
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import Q

from hier.models import get_app_params
from hier.aside import Fix
from hier.utils import get_base_context_ext, process_common_commands, sort_data, extract_get_params
from hier.params import get_search_mode, get_search_info, set_restriction, set_article_kind, set_article_visible
from .models import app_name, Biomarker, Incident, Anamnesis
from .forms import BiomarkerForm, IncidentForm

items_in_page = 20

CHRONO = 'chrono'
BIOMARK = 'biomark'
INCIDENT = 'incident'

#----------------------------------
def chrono(request):
    set_restriction(request.user, app_name, CHRONO)
    return HttpResponseRedirect(reverse('health:main'))

#----------------------------------
def biomark(request):
    set_restriction(request.user, app_name, BIOMARK)
    return HttpResponseRedirect(reverse('health:main'))

#----------------------------------
def incident(request):
    set_restriction(request.user, app_name, INCIDENT)
    return HttpResponseRedirect(reverse('health:main'))

#----------------------------------
def item_form(request, pk):
    set_article_kind(request.user, app_name, 'item', pk)
    return HttpResponseRedirect(reverse('health:main') + extract_get_params(request))

#----------------------------------
@login_required(login_url='account:login')
def main(request):
    app_param = get_app_params(request.user, app_name)
    if (app_param.restriction != CHRONO) and (app_param.restriction != BIOMARK) and (app_param.restriction != INCIDENT):
        set_restriction(request.user, app_name, CHRONO)
        app_param = get_app_params(request.user, app_name)

    if process_common_commands(request, app_name): # aside open/close, article open/close
        return HttpResponseRedirect(reverse('health:main') + extract_get_params(request))

    app_param, context = get_base_context_ext(request, app_name, 'health', get_title(app_param.restriction))

    if (request.method == 'POST'):
        if ('item-add' in request.POST):
            item = None
            if (app_param.restriction == BIOMARK):
                item = create_biomarkers(request.user, request.POST['item_add-name'])
            if (app_param.restriction == INCIDENT):
                item = Incident.objects.create(user = request.user, name = request.POST['item_add-name'], beg = datetime.now(), end = datetime.now())
            if item:
                return HttpResponseRedirect(reverse('health:item_form', args = [item.id]))

    fixes = []
    fixes.append(Fix(CHRONO, _('chronology').capitalize(), 'rok/icon/all.png', 'chrono/', None))
    fixes.append(Fix(BIOMARK, _('biomarkers').capitalize(), 'rok/icon/all.png', 'biomark/', len(Biomarker.objects.filter(user = request.user.id))))
    fixes.append(Fix(INCIDENT, _('incidents').capitalize(), 'rok/icon/all.png', 'incident/', len(Incident.objects.filter(user = request.user.id))))
    context['fix_list'] = fixes
    context['without_lists'] = True
    context['add_item_placeholder'] = get_placeholder(app_param.restriction)
    context['hide_selector'] = True
    context['hide_important'] = True
    if (app_param.restriction == CHRONO):
        context['hide_add_item_input'] = True
        context['temperatures'], dt_start = get_temp_points(request.user)
        context['incidents'] = get_incidents(request.user, dt_start)
        context['weights'] = get_weight_points(request.user)
        context['waists'] = get_waist_points(request.user)

    redirect = False

    if app_param.article:
        valid_article = False
        if (app_param.restriction == BIOMARK):
            valid_article = Biomarker.objects.filter(id = app_param.art_id, user = request.user.id).exists()
        if (app_param.restriction == INCIDENT):
            valid_article = Incident.objects.filter(id = app_param.art_id, user = request.user.id).exists()
        if valid_article:
            if (app_param.restriction == BIOMARK):
                item = get_object_or_404(Biomarker.objects.filter(id = app_param.art_id, user = request.user.id))
                redirect = edit_item(request, context, app_param.restriction, item, False)
            if (app_param.restriction == INCIDENT):
                item = get_object_or_404(Incident.objects.filter(id = app_param.art_id, user = request.user.id))
                disable_delete = Anamnesis.objects.filter(incident = item.id).exists()
                redirect = edit_item(request, context, app_param.restriction, item, disable_delete)
        else:
            set_article_visible(request.user, app_name, False)
            redirect = True
    
    if redirect:
        return HttpResponseRedirect(reverse('health:main') + extract_get_params(request))

    query = None
    if request.method == 'GET':
        query = request.GET.get('q')
    data = filtered_sorted_list(request.user, app_param, query)

    page_number = 1
    if (request.method == 'GET'):
        page_number = request.GET.get('page')
    paginator = Paginator(data, items_in_page)
    page_obj = paginator.get_page(page_number)
    context['page_obj'] = paginator.get_page(page_number)
    context['search_info'] = get_search_info(query)
    template = loader.get_template('health/' + app_param.restriction + '.html')
    return HttpResponse(template.render(context, request))


#----------------------------------
def filtered_sorted_list(user, app_param, query):
    data = filtered_list(user, app_param.restriction, query, app_param.lst)
    return data

#----------------------------------
def filtered_list(user, restriction, query = None, lst = None):
    if (restriction == BIOMARK):
        data = Biomarker.objects.filter(user = user.id).order_by('-publ')
    elif (restriction == INCIDENT):
        data = Incident.objects.filter(user = user.id).order_by('-beg')
    else:
        data = []

    if not query:
        return data

    """
    search_mode = get_search_mode(query)
    lookups = None
    if (search_mode == 0):
        return data
    elif (search_mode == 1):
        lookups = Q(name__icontains=query) | Q(code__icontains=query) | Q(descr__icontains=query) | Q(url__icontains=query)
    elif (search_mode == 2):
        lookups = Q(categories__icontains=query[1:])
    
    return data.filter(lookups).distinct()
    """
    return data
#----------------------------------
def get_title(restriction):
    if (restriction == CHRONO):
        return _('dynamics of changes in biomarkers').capitalize()
    if (restriction == BIOMARK):
        return _('biomarkers').capitalize()
    if (restriction == INCIDENT):
        return _('incidents').capitalize()

#----------------------------------
def get_placeholder(restriction):
    if (restriction == BIOMARK):
        return _('add biomarkers').capitalize()
    if (restriction == INCIDENT):
        return _('add incident').capitalize()
    return None

#----------------------------------
def edit_item(request, context, restriction, item, disable_delete = False):
    form = None
    if (request.method == 'POST'):
        if ('item_delete' in request.POST):
            delete_item(request, item, disable_delete)
            return True
        if ('item_save' in request.POST):
            if (restriction == BIOMARK):
                form = BiomarkerForm(request.POST, instance = item)
            elif (restriction == INCIDENT):
                form = IncidentForm(request.POST, instance = item)
            if form.is_valid():
                data = form.save(commit = False)
                data.user = request.user
                form.save()
                return True

    if not form:
        if (restriction == BIOMARK):
            form = BiomarkerForm(instance = item)
        elif (restriction == INCIDENT):
            form = IncidentForm(instance = item)

    context['form'] = form
    context['ed_item'] = item
    return False

#----------------------------------
def delete_item(request, item, disable_delete = False):
    if disable_delete:
        return False
    item.delete()
    set_article_visible(request.user, app_name, False)
    return True

#----------------------------------
def create_biomarkers(user, s_value):
    height = None
    weight = None
    temp = None
    waist = None
    systolic = None
    diastolic = None
    pulse = None
    info = ''
    n_value = 0

    try:
        n_value = float(s_value.replace(',', '.'))
    except ValueError:
        info = s_value

    if (n_value >= 35) and (n_value < 50):
        temp = n_value
    elif (n_value >= 50) and (n_value < 150):
        weight = n_value
    elif (n_value >= 150) and (n_value < 250):
        height = n_value
    
    return Biomarker.objects.create(user = user, height = height, weight = weight, temp = temp, waist = waist, \
                                    systolic = systolic, diastolic = diastolic, pulse = pulse, info = info, publ = datetime.now())


#----------------------------------
def get_x_for_any(dt_min):
    """lambda function to convert any date value to X coordinate in a chart"""
    return lambda dt : int((dt - dt_min).days / (datetime.now().date() - dt_min).days * 1000)

#----------------------------------
def get_y_for_any(min_value, max_value):
    """lambda function to convert any phisical value to Y coordinate in a chart"""
    return lambda value : 100 - int((value - min_value) / (max_value - min_value) * 100)

#----------------------------------
def get_incidents(user, dt_start):
    incidents = []
    get_x_for_temp = get_x_for_any(dt_start)
    for y in Incident.objects.filter(user = user.id).order_by('beg'):
        x1_pos = get_x_for_temp(y.beg)
        x2_pos = get_x_for_temp(y.end)
        incidents.append({'x': x1_pos, 'width': x2_pos - x1_pos})
    return incidents

#----------------------------------
def get_temp_points(user):
    get_y_for_temp = get_y_for_any(35, 40)
    points = []
    dt_start = None
    for x in Biomarker.objects.filter(user = user.id).order_by('publ'):
        if not dt_start and x.temp:
            dt_start = (x.publ - timedelta(2)).date()
            get_x_for_temp = get_x_for_any(dt_start)
        if x.temp:
            x_pos = get_x_for_temp(x.publ.date())
            y_pos = get_y_for_temp(x.temp)
            if (x.temp >= 37):
                color = "red"
            else:
                color = "green"
            points.append({'x': x_pos, 'y': y_pos, 'color': color})
    
    return points, dt_start

#----------------------------------
def get_weight_points(user):
    get_y_for_weight = get_y_for_any(70, 95)
    points = []
    dt_start = None
    for x in Biomarker.objects.filter(user = user.id).order_by('publ'):
        if not dt_start and x.weight:
            dt_start = (x.publ - timedelta(2)).date()
            get_x_for_weight = get_x_for_any(dt_start)
        if x.weight:
            x_pos = get_x_for_weight(x.publ.date())
            y_pos = get_y_for_weight(x.weight)
            if (x.weight >= 73):
                color = "red"
            else:
                color = "green"
            points.append({'x': x_pos, 'y': y_pos, 'color': color})
    
    return points

#----------------------------------
def get_waist_points(user):
    get_y_for_waist = get_y_for_any(80, 105)
    points = []
    dt_start = None
    for x in Biomarker.objects.filter(user = user.id).order_by('publ'):
        if not dt_start and x.waist:
            dt_start = (x.publ - timedelta(2)).date()
            get_x_for_waist = get_x_for_any(dt_start)
        if x.waist:
            x_pos = get_x_for_waist(x.publ.date())
            y_pos = get_y_for_waist(x.waist)
            points.append({'x': x_pos, 'y': y_pos, 'color': "black"})
    
    return points



