from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, redirect
from django.views.generic import UpdateView, TemplateView, FormView
from django.contrib.auth.mixins import PermissionRequiredMixin
from admin.rdm_useremails.forms import SearchForm

from django.db.models import Q
from osf.models.user import OSFUser

from django.urls import reverse

from django.views.defaults import page_not_found

class SearchView(PermissionRequiredMixin, FormView):
    template_name = 'rdm_useremails/search.html'
    object_type = 'osfuser'
    permission_required = 'osf.view_osfuser'
    raise_exception = True
    form_class = SearchForm
    context_object_name = 'user'

    def __init__(self, *args, **kwargs):
        self.redirect_url = None
        super(SearchView, self).__init__(*args, **kwargs)

    def form_valid(self, form):
        guid = form.cleaned_data['guid']
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']


    @property
    def success_url(self):
        return self.redirect_url

class ResultView(PermissionRequiredMixin, TemplateView):
    template_name = 'rdm_useremails/result.html'


class SettingsView(PermissionRequiredMixin, TemplateView):
    template_name = 'rdm_useremails/settings.html'


