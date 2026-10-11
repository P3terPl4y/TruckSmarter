from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from core.permissions import admin_required
from .forms import OfferForm
from .models import Sale
from . import workflow


@login_required
@require_POST
def reserve_vehicle(request, vehicle_id):
    try:
        workflow.reserve(vehicle_id, request.user)
        messages.success(request, "¡Vehículo reservado!")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("vehicles:detail", pk=vehicle_id)


@login_required
@require_POST
def cancel_reservation(request, vehicle_id):
    workflow.cancel_reservation(vehicle_id, request.user)
    messages.info(request, "Has cancelado la reserva.")
    return redirect("vehicles:detail", pk=vehicle_id)


@login_required
def purchase_history(request):
    sales = Sale.objects.filter(buyer=request.user).select_related(
        "vehicle__brand", "seller"
    )
    page = Paginator(sales, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "sales/history.html",
        {"sales": page, "page_obj": page, "is_paginated": page.has_other_pages()},
    )


@login_required
@require_POST
def make_offer(request, vehicle_id):
    form = OfferForm(request.POST)
    if form.is_valid():
        try:
            workflow.create_offer(
                vehicle_id,
                request.user,
                form.cleaned_data["offered_price"],
                form.cleaned_data["offer_comment"],
            )
            messages.success(request, "¡Oferta enviada! Está en revisión.")
        except ValueError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(
            request, "Ingresa un precio válido y un comentario de hasta 650 caracteres."
        )
    return redirect("vehicles:detail", pk=vehicle_id)


@admin_required
@require_POST
def accept_offer(request, sale_id):
    workflow.decide_offer(sale_id, request.user, accept=True)
    messages.success(request, "Oferta aceptada.")
    return redirect("dashboard:offer_list")


@admin_required
@require_POST
def reject_offer(request, sale_id):
    workflow.decide_offer(sale_id, request.user, accept=False)
    messages.info(request, "Oferta rechazada.")
    return redirect("dashboard:offer_list")
