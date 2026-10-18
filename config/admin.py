"""Sitio de administración técnico: solo superusuarios activos."""

from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache

from config.limites import LimiteIngresoMixin


class LoginAdministracion(LimiteIngresoMixin, LoginView):
    """Login del admin con los mismos baldes de fallos que el del panel."""


class SitioAdministracion(AdminSite):
    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    @method_decorator(never_cache)
    def login(self, request, extra_context=None):
        """Igual que `AdminSite.login`, pero con el límite de intentos fallidos."""
        if request.method == "GET" and self.has_permission(request):
            return HttpResponseRedirect(reverse("admin:index", current_app=self.name))

        contexto = {
            **self.each_context(request),
            "title": _("Log in"),
            "subtitle": None,
            "app_path": request.get_full_path(),
            "username": request.user.get_username(),
        }
        if (
            REDIRECT_FIELD_NAME not in request.GET
            and REDIRECT_FIELD_NAME not in request.POST
        ):
            contexto[REDIRECT_FIELD_NAME] = reverse(
                "admin:index", current_app=self.name
            )
        contexto.update(extra_context or {})

        request.current_app = self.name
        return LoginAdministracion.as_view(
            extra_context=contexto,
            authentication_form=self.login_form or AdminAuthenticationForm,
            template_name=self.login_template or "admin/login.html",
        )(request)
